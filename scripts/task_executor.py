#!/usr/bin/env python3
"""
Gold Standard Task Executor
Executes action insights extracted from reports before the next analysis cycle.
Transforms the system from passive "showing" to active "doing".

PERSISTENCE MODE: Tasks are executed until completion. On quota errors,
the executor waits and retries. All completed research is published to Notion.
"""
import os
import sys
import json
import re
import time
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import yfinance as yf
except ImportError:
    yf = None


# ==========================================
# RETRY CONFIGURATION
# ==========================================

# Retry settings for AI quota issues
MAX_RETRIES = 10
INITIAL_BACKOFF_SECONDS = 30
MAX_BACKOFF_SECONDS = 600  # 10 minutes max wait
QUOTA_ERROR_PATTERNS = [
    'quota', 'rate limit', 'too many requests', '429', 
    'resource exhausted', 'capacity', 'overloaded'
]


# ==========================================
# TASK RESULT
# ==========================================

@dataclass
class TaskResult:
    """Result of a task execution."""
    action_id: str
    success: bool
    result_data: Any
    execution_time_ms: float
    error_message: Optional[str] = None
    artifacts: List[str] = None  # File paths created
    retries: int = 0
    
    def __post_init__(self):
        if self.artifacts is None:
            self.artifacts = []


# ==========================================
# TASK EXECUTOR
# ==========================================

class TaskExecutor:
    """
    Executes action insights from the InsightsExtractor.
    Runs ALL tasks to completion, with retry logic for quota issues.
    Publishes completed research to Notion automatically.
    """
    
    def __init__(self, config, logger: logging.Logger, model=None, insights_extractor=None):
        self.config = config
        self.logger = logger
        self.model = model
        self.insights_extractor = insights_extractor
        self.output_dir = Path(config.OUTPUT_DIR) if config else PROJECT_ROOT / "output"
        self.research_dir = self.output_dir / "research"
        self.research_dir.mkdir(parents=True, exist_ok=True)
        
        # Task handlers registry
        self.handlers: Dict[str, Callable] = {
            'research': self._handle_research,
            'data_fetch': self._handle_data_fetch,
            'news_scan': self._handle_news_scan,
            'calculation': self._handle_calculation,
            'monitoring': self._handle_monitoring,
            'code_task': self._handle_code_task,
        }
        
        # Execution statistics
        self.stats = {
            'total_executed': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'retried': 0,
            'total_time_ms': 0,
            'notion_published': 0
        }
        
        # Notion publisher (lazy loaded)
        self._notion_publisher = None
    
    def _get_notion_publisher(self):
        """Lazy load Notion publisher."""
        if self._notion_publisher is None:
            try:
                from scripts.notion_publisher import NotionPublisher
                self._notion_publisher = NotionPublisher()
                self.logger.info("[EXECUTOR] Notion publisher initialized")
            except Exception as e:
                self.logger.warning(f"[EXECUTOR] Notion publisher not available: {e}")
        return self._notion_publisher
    
    def _is_quota_error(self, error_msg: str) -> bool:
        """Check if an error is a quota/rate limit error."""
        error_lower = str(error_msg).lower()
        return any(pattern in error_lower for pattern in QUOTA_ERROR_PATTERNS)
    
    def _wait_for_quota(self, retry_count: int) -> int:
        """Calculate and wait for quota reset. Returns seconds waited."""
        backoff = min(INITIAL_BACKOFF_SECONDS * (2 ** retry_count), MAX_BACKOFF_SECONDS)
        self.logger.warning(f"[EXECUTOR] Quota limit hit. Waiting {backoff}s before retry {retry_count + 1}/{MAX_RETRIES}...")
        print(f"[EXECUTOR] ⏳ Waiting {backoff}s for API quota reset (retry {retry_count + 1}/{MAX_RETRIES})...")
        time.sleep(backoff)
        return backoff
    
    def _execute_with_retry(self, action, handler: Callable) -> TaskResult:
        """Execute a task with retry logic for quota errors."""
        last_error = None
        
        for retry in range(MAX_RETRIES + 1):
            try:
                result = handler(action)
                
                if result.success:
                    result.retries = retry
                    return result
                
                # Check if failure is due to quota
                if result.error_message and self._is_quota_error(result.error_message):
                    if retry < MAX_RETRIES:
                        self._wait_for_quota(retry)
                        self.stats['retried'] += 1
                        continue
                
                # Non-quota error, return failure
                return result
                
            except Exception as e:
                last_error = str(e)
                if self._is_quota_error(last_error):
                    if retry < MAX_RETRIES:
                        self._wait_for_quota(retry)
                        self.stats['retried'] += 1
                        continue
                
                return TaskResult(
                    action_id=action.action_id,
                    success=False,
                    result_data=None,
                    execution_time_ms=0,
                    error_message=last_error,
                    retries=retry
                )
        
        # All retries exhausted
        return TaskResult(
            action_id=action.action_id,
            success=False,
            result_data=None,
            execution_time_ms=0,
            error_message=f"Max retries ({MAX_RETRIES}) exceeded. Last error: {last_error}",
            retries=MAX_RETRIES
        )
    
    def _publish_to_notion(self, filepath: str, doc_type: str = 'research') -> bool:
        """Publish a completed research file to Notion."""
        publisher = self._get_notion_publisher()
        if not publisher:
            return False
        
        try:
            result = publisher.sync_file(filepath, doc_type=doc_type, force=True)
            if not result.get('skipped'):
                self.stats['notion_published'] += 1
                self.logger.info(f"[EXECUTOR] Published to Notion: {Path(filepath).name}")
                return True
        except Exception as e:
            self.logger.warning(f"[EXECUTOR] Failed to publish to Notion: {e}")
        return False

    def execute_all_pending(self, max_tasks: int = None, timeout_per_task: int = 300) -> List[TaskResult]:
        """
        Execute ALL pending actions until completion.
        
        Args:
            max_tasks: Optional limit (None = process ALL tasks)
            timeout_per_task: Timeout per task in seconds (default 5 min)
            
        Returns list of TaskResults.
        """
        if not self.insights_extractor:
            self.logger.warning("[EXECUTOR] No insights extractor configured")
            return []
        
        pending = self.insights_extractor.get_pending_actions()
        self.logger.info(f"[EXECUTOR] Found {len(pending)} pending tasks")
        print(f"[EXECUTOR] 📋 Processing {len(pending)} pending tasks...")
        
        if not pending:
            return []
        
        # Process all tasks unless max_tasks specified
        tasks_to_execute = pending if max_tasks is None else pending[:max_tasks]
        results = []
        
        for i, action in enumerate(tasks_to_execute, 1):
            try:
                print(f"[EXECUTOR] 🔄 Task {i}/{len(tasks_to_execute)}: {action.title[:50]}...")
                
                # Mark as in progress
                action.status = 'in_progress'
                
                # Get the handler
                handler = self.handlers.get(action.action_type)
                if not handler:
                    result = TaskResult(
                        action_id=action.action_id,
                        success=False,
                        result_data=None,
                        execution_time_ms=0,
                        error_message=f"Unknown action type: {action.action_type}"
                    )
                else:
                    # Execute with retry logic for quota errors
                    start_time = time.time()
                    result = self._execute_with_retry(action, handler)
                    execution_time = (time.time() - start_time) * 1000
                    result.execution_time_ms = execution_time
                
                results.append(result)
                
                # Update statistics
                self.stats['total_executed'] += 1
                self.stats['total_time_ms'] += result.execution_time_ms
                
                if result.success:
                    self.stats['successful'] += 1
                    print(f"[EXECUTOR] ✅ Completed: {action.title[:40]}")
                    
                    self.insights_extractor.mark_action_complete(
                        action.action_id, 
                        json.dumps(result.result_data) if isinstance(result.result_data, dict) else str(result.result_data)
                    )
                    
                    # Publish artifacts to Notion
                    if result.artifacts:
                        for artifact_path in result.artifacts:
                            if artifact_path.endswith('.md'):
                                self._publish_to_notion(artifact_path, doc_type='research')
                            elif artifact_path.endswith('.json'):
                                # Convert JSON to markdown for Notion
                                self._convert_and_publish_json(artifact_path)
                else:
                    self.stats['failed'] += 1
                    print(f"[EXECUTOR] ❌ Failed: {action.title[:40]} - {result.error_message[:50] if result.error_message else 'Unknown'}")
                    self.insights_extractor.mark_action_failed(action.action_id, result.error_message)
                
            except Exception as e:
                self.logger.error(f"[EXECUTOR] Error executing {action.action_id}: {e}")
                self.stats['failed'] += 1
                results.append(TaskResult(
                    action_id=action.action_id,
                    success=False,
                    result_data=None,
                    execution_time_ms=0,
                    error_message=str(e)
                ))
        
        self._log_summary(results)
        return results
    
    def _convert_and_publish_json(self, json_path: str) -> bool:
        """Convert a JSON data file to markdown and publish to Notion."""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Create markdown version
            md_path = json_path.replace('.json', '.md')
            
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(f"# Data Report: {Path(json_path).stem}\n\n")
                f.write(f"**Generated:** {data.get('fetched_at', datetime.now().isoformat())}\n")
                f.write(f"**Action ID:** {data.get('action_id', 'N/A')}\n\n")
                f.write("---\n\n")
                
                # Format the data nicely
                if 'data' in data:
                    for key, value in data['data'].items():
                        f.write(f"## {key.replace('_', ' ').title()}\n\n")
                        if isinstance(value, dict):
                            for k, v in value.items():
                                f.write(f"- **{k}**: {v}\n")
                        else:
                            f.write(f"{value}\n")
                        f.write("\n")
            
            # Publish the markdown
            return self._publish_to_notion(md_path, doc_type='research')
            
        except Exception as e:
            self.logger.warning(f"[EXECUTOR] Failed to convert JSON to markdown: {e}")
            return False
    
    def _execute_single(self, action, timeout: int) -> TaskResult:
        """Execute a single action (legacy method, use _execute_with_retry instead)."""
        handler = self.handlers.get(action.action_type)
        
        if not handler:
            return TaskResult(
                action_id=action.action_id,
                success=False,
                result_data=None,
                execution_time_ms=0,
                error_message=f"Unknown action type: {action.action_type}"
            )
        
        return self._execute_with_retry(action, handler)
    
    # ==========================================
    # TASK HANDLERS
    # ==========================================
    
    def _handle_research(self, action) -> TaskResult:
        """Handle research tasks using AI."""
        self.logger.info(f"[EXECUTOR] Researching: {action.title}")
        
        if not self.model:
            return TaskResult(
                action_id=action.action_id,
                success=False,
                result_data=None,
                execution_time_ms=0,
                error_message="AI model not available for research"
            )
        
        # Build research prompt
        prompt = f"""You are a financial research analyst. Conduct brief, focused research on the following topic:

Topic: {action.title}
Context: {action.description}
Source: {action.source_context[:500] if action.source_context else 'N/A'}

Provide a concise research summary (200-400 words) covering:
1. Key facts and current state
2. Relevance to gold/precious metals
3. Potential market impact
4. Recommended next steps

Be specific and actionable. Include any relevant numbers or data points."""

        try:
            response = self.model.generate_content(prompt)
            result_text = response.text
            
            # Save research to file
            filename = f"research_{action.action_id}_{date.today()}.md"
            filepath = self.research_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"# Research: {action.title}\n\n")
                f.write(f"**Generated:** {datetime.now().isoformat()}\n")
                f.write(f"**Action ID:** {action.action_id}\n")
                f.write(f"**Priority:** {action.priority}\n\n")
                f.write("---\n\n")
                f.write(result_text)
            
            return TaskResult(
                action_id=action.action_id,
                success=True,
                result_data={'summary': result_text[:500], 'full_path': str(filepath)},
                execution_time_ms=0,
                artifacts=[str(filepath)]
            )
            
        except Exception as e:
            return TaskResult(
                action_id=action.action_id,
                success=False,
                result_data=None,
                execution_time_ms=0,
                error_message=str(e)
            )
    
    def _handle_data_fetch(self, action) -> TaskResult:
        """Handle data fetching tasks."""
        self.logger.info(f"[EXECUTOR] Fetching data: {action.title}")
        
        # Parse what data to fetch from action title/description
        combined = f"{action.title} {action.description}".lower()
        
        result_data = {}
        
        # Check for COT/positioning data request
        if 'cot' in combined or 'positioning' in combined or 'commitment' in combined:
            result_data['cot'] = "COT data requires CFTC API integration - logged for future fetch"
            result_data['note'] = "Recommend checking: https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm"
        
        # Check for ETF flow data
        if 'etf' in combined or 'flow' in combined or 'gld' in combined or 'slv' in combined:
            if yf:
                try:
                    # Get GLD and SLV data
                    gld = yf.Ticker('GLD')
                    slv = yf.Ticker('SLV')
                    
                    gld_info = gld.info
                    slv_info = slv.info
                    
                    result_data['etf_data'] = {
                        'GLD': {
                            'price': gld_info.get('regularMarketPrice'),
                            'volume': gld_info.get('regularMarketVolume'),
                            'avg_volume': gld_info.get('averageVolume'),
                            'total_assets': gld_info.get('totalAssets'),
                        },
                        'SLV': {
                            'price': slv_info.get('regularMarketPrice'),
                            'volume': slv_info.get('regularMarketVolume'),
                            'avg_volume': slv_info.get('averageVolume'),
                            'total_assets': slv_info.get('totalAssets'),
                        }
                    }
                except Exception as e:
                    result_data['etf_error'] = str(e)
        
        # Check for yield/treasury data
        if 'yield' in combined or 'treasury' in combined or '10y' in combined or '10-year' in combined:
            if yf:
                try:
                    tnx = yf.Ticker('^TNX')
                    hist = tnx.history(period='5d')
                    if not hist.empty:
                        result_data['yield_10y'] = {
                            'current': float(hist['Close'].iloc[-1]),
                            'previous': float(hist['Close'].iloc[-2]) if len(hist) > 1 else None,
                            'week_ago': float(hist['Close'].iloc[0]) if len(hist) >= 5 else None,
                        }
                except Exception as e:
                    result_data['yield_error'] = str(e)
        
        # Check for DXY data
        if 'dxy' in combined or 'dollar' in combined:
            if yf:
                try:
                    dxy = yf.Ticker('DX-Y.NYB')
                    hist = dxy.history(period='5d')
                    if not hist.empty:
                        result_data['dxy'] = {
                            'current': float(hist['Close'].iloc[-1]),
                            'previous': float(hist['Close'].iloc[-2]) if len(hist) > 1 else None,
                        }
                except Exception as e:
                    result_data['dxy_error'] = str(e)
        
        if result_data:
            # Save data to file
            filename = f"data_fetch_{action.action_id}_{date.today()}.json"
            filepath = self.research_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    'action_id': action.action_id,
                    'fetched_at': datetime.now().isoformat(),
                    'data': result_data
                }, f, indent=2)
            
            return TaskResult(
                action_id=action.action_id,
                success=True,
                result_data=result_data,
                execution_time_ms=0,
                artifacts=[str(filepath)]
            )
        
        return TaskResult(
            action_id=action.action_id,
            success=False,
            result_data=None,
            execution_time_ms=0,
            error_message="Could not determine what data to fetch"
        )
    
    def _handle_news_scan(self, action) -> TaskResult:
        """Handle news scanning tasks."""
        self.logger.info(f"[EXECUTOR] Scanning news: {action.title}")
        
        if not self.model:
            return TaskResult(
                action_id=action.action_id,
                success=False,
                result_data=None,
                execution_time_ms=0,
                error_message="AI model not available for news analysis"
            )
        
        # Get news from yfinance for relevant tickers
        news_items = []
        
        if yf:
            tickers_to_check = ['GC=F', '^TNX', 'DX-Y.NYB', '^VIX', '^GSPC']
            
            for ticker in tickers_to_check:
                try:
                    t = yf.Ticker(ticker)
                    if hasattr(t, 'news') and t.news:
                        for item in t.news[:3]:
                            news_items.append({
                                'ticker': ticker,
                                'title': item.get('title', ''),
                                'publisher': item.get('publisher', ''),
                                'link': item.get('link', ''),
                            })
                except Exception:
                    continue
        
        # Use AI to analyze relevance
        if news_items:
            prompt = f"""Analyze these financial news headlines for relevance to gold and precious metals trading:

News Headlines:
{json.dumps(news_items, indent=2)}

Task Context: {action.description}

For each headline, rate relevance (1-10) and explain potential gold impact in 1-2 sentences.
Focus on actionable insights for a gold trader."""

            try:
                response = self.model.generate_content(prompt)
                analysis = response.text
                
                # Save analysis
                filename = f"news_scan_{action.action_id}_{date.today()}.md"
                filepath = self.research_dir / filename
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"# News Scan: {action.title}\n\n")
                    f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
                    f.write("## Headlines Analyzed\n\n")
                    for item in news_items:
                        f.write(f"- **{item['ticker']}**: {item['title']}\n")
                    f.write("\n## Analysis\n\n")
                    f.write(analysis)
                
                return TaskResult(
                    action_id=action.action_id,
                    success=True,
                    result_data={'headlines_count': len(news_items), 'analysis_preview': analysis[:300]},
                    execution_time_ms=0,
                    artifacts=[str(filepath)]
                )
            except Exception as e:
                return TaskResult(
                    action_id=action.action_id,
                    success=False,
                    result_data=None,
                    execution_time_ms=0,
                    error_message=str(e)
                )
        
        return TaskResult(
            action_id=action.action_id,
            success=True,
            result_data={'note': 'No relevant news found'},
            execution_time_ms=0
        )
    
    def _handle_calculation(self, action) -> TaskResult:
        """Handle calculation tasks."""
        self.logger.info(f"[EXECUTOR] Calculating: {action.title}")
        
        combined = f"{action.title} {action.description}".lower()
        result_data = {}
        
        # Position sizing calculation
        if 'position' in combined and 'size' in combined or 'sizing' in combined:
            # Get current ATR from gold
            if yf:
                try:
                    gc = yf.download('GC=F', period='20d', progress=False)
                    if not gc.empty:
                        # Calculate ATR
                        high = gc['High']
                        low = gc['Low']
                        close = gc['Close']
                        
                        tr1 = high - low
                        tr2 = abs(high - close.shift(1))
                        tr3 = abs(low - close.shift(1))
                        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                        atr = tr.rolling(14).mean().iloc[-1]
                        
                        current_price = float(close.iloc[-1])
                        
                        # Calculate position size for different risk levels
                        account_sizes = [10000, 50000, 100000]
                        risk_percents = [0.01, 0.02, 0.03]
                        
                        result_data['position_sizing'] = {
                            'current_price': current_price,
                            'atr_14': float(atr),
                            'recommended_stop': float(current_price - (2 * atr)),
                            'calculations': []
                        }
                        
                        for account in account_sizes:
                            for risk_pct in risk_percents:
                                risk_amount = account * risk_pct
                                stop_distance = 2 * atr
                                position_size = risk_amount / stop_distance
                                
                                result_data['position_sizing']['calculations'].append({
                                    'account_size': account,
                                    'risk_percent': risk_pct * 100,
                                    'risk_amount': risk_amount,
                                    'position_size_oz': round(position_size, 2),
                                    'position_value': round(position_size * current_price, 2)
                                })
                except Exception as e:
                    result_data['error'] = str(e)
        
        # Risk/reward calculation
        if 'risk' in combined and 'reward' in combined or 'r:r' in combined:
            # Extract levels from context if available
            levels = re.findall(r'\$?([\d,]+(?:\.\d+)?)', action.source_context or '')
            if len(levels) >= 3:
                try:
                    entry = float(levels[0].replace(',', ''))
                    stop = float(levels[1].replace(',', ''))
                    target = float(levels[2].replace(',', ''))
                    
                    risk = abs(entry - stop)
                    reward = abs(target - entry)
                    rr_ratio = reward / risk if risk > 0 else 0
                    
                    result_data['risk_reward'] = {
                        'entry': entry,
                        'stop_loss': stop,
                        'target': target,
                        'risk_points': risk,
                        'reward_points': reward,
                        'risk_reward_ratio': round(rr_ratio, 2),
                        'recommendation': 'Favorable' if rr_ratio >= 2 else 'Marginal' if rr_ratio >= 1.5 else 'Unfavorable'
                    }
                except Exception:
                    pass
        
        if result_data:
            # Save calculations
            filename = f"calc_{action.action_id}_{date.today()}.json"
            filepath = self.research_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    'action_id': action.action_id,
                    'calculated_at': datetime.now().isoformat(),
                    'results': result_data
                }, f, indent=2)
            
            return TaskResult(
                action_id=action.action_id,
                success=True,
                result_data=result_data,
                execution_time_ms=0,
                artifacts=[str(filepath)]
            )
        
        return TaskResult(
            action_id=action.action_id,
            success=False,
            result_data=None,
            execution_time_ms=0,
            error_message="Could not determine calculation type"
        )
    
    def _handle_monitoring(self, action) -> TaskResult:
        """Handle monitoring tasks - set up alerts/tracking."""
        self.logger.info(f"[EXECUTOR] Setting up monitoring: {action.title}")
        
        # Extract price levels from action
        levels = re.findall(r'\$?([\d,]+(?:\.\d+)?)', f"{action.title} {action.description}")
        
        monitoring_config = {
            'action_id': action.action_id,
            'created_at': datetime.now().isoformat(),
            'status': 'active',
            'levels_to_watch': [],
            'conditions': []
        }
        
        for level in levels:
            try:
                price = float(level.replace(',', ''))
                if 1000 < price < 10000:  # Likely a gold price
                    monitoring_config['levels_to_watch'].append({
                        'price': price,
                        'type': 'price_level',
                        'triggered': False
                    })
            except ValueError:
                continue
        
        # Extract condition keywords
        combined = f"{action.title} {action.description}".lower()
        
        if 'breakout' in combined:
            monitoring_config['conditions'].append({'type': 'breakout', 'direction': 'above'})
        if 'breakdown' in combined:
            monitoring_config['conditions'].append({'type': 'breakdown', 'direction': 'below'})
        if 'support' in combined:
            monitoring_config['conditions'].append({'type': 'support_test'})
        if 'resistance' in combined:
            monitoring_config['conditions'].append({'type': 'resistance_test'})
        
        # Save monitoring config
        filename = f"monitor_{action.action_id}_{date.today()}.json"
        filepath = self.research_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(monitoring_config, f, indent=2)
        
        return TaskResult(
            action_id=action.action_id,
            success=True,
            result_data=monitoring_config,
            execution_time_ms=0,
            artifacts=[str(filepath)]
        )
    
    def _handle_code_task(self, action) -> TaskResult:
        """Handle code generation/analysis tasks."""
        self.logger.info(f"[EXECUTOR] Code task: {action.title}")
        
        if not self.model:
            return TaskResult(
                action_id=action.action_id,
                success=False,
                result_data=None,
                execution_time_ms=0,
                error_message="AI model not available for code tasks"
            )
        
        prompt = f"""Generate Python code for the following financial analysis task:

Task: {action.title}
Details: {action.description}
Context: {action.source_context[:500] if action.source_context else 'N/A'}

Requirements:
1. Use pandas for data manipulation
2. Include error handling
3. Add comments explaining the logic
4. Make it production-ready

Provide the complete Python code."""

        try:
            response = self.model.generate_content(prompt)
            code = response.text
            
            # Extract code from markdown if present
            code_match = re.search(r'```python\n(.*?)```', code, re.DOTALL)
            if code_match:
                code = code_match.group(1)
            
            # Save code to file
            filename = f"code_{action.action_id}_{date.today()}.py"
            filepath = self.research_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f'"""\nGenerated for: {action.title}\nAction ID: {action.action_id}\nGenerated: {datetime.now().isoformat()}\n"""\n\n')
                f.write(code)
            
            return TaskResult(
                action_id=action.action_id,
                success=True,
                result_data={'code_preview': code[:300], 'filepath': str(filepath)},
                execution_time_ms=0,
                artifacts=[str(filepath)]
            )
        except Exception as e:
            return TaskResult(
                action_id=action.action_id,
                success=False,
                result_data=None,
                execution_time_ms=0,
                error_message=str(e)
            )
    
    def _log_summary(self, results: List[TaskResult]):
        """Log execution summary."""
        successful = sum(1 for r in results if r.success)
        failed = sum(1 for r in results if not r.success)
        total_time = sum(r.execution_time_ms for r in results)
        total_retries = sum(r.retries for r in results)
        
        print("\n" + "=" * 50)
        print("[EXECUTOR] 📊 Execution Summary")
        print("=" * 50)
        print(f"  Total Tasks:      {len(results)}")
        print(f"  ✅ Successful:    {successful}")
        print(f"  ❌ Failed:        {failed}")
        print(f"  🔄 Total Retries: {total_retries}")
        print(f"  📤 Notion Published: {self.stats.get('notion_published', 0)}")
        print(f"  ⏱️  Total Time:    {total_time/1000:.1f}s")
        print("=" * 50 + "\n")
        
        self.logger.info("=" * 50)
        self.logger.info("[EXECUTOR] Execution Summary")
        self.logger.info(f"  Total Tasks: {len(results)}")
        self.logger.info(f"  Successful: {successful}")
        self.logger.info(f"  Failed: {failed}")
        self.logger.info(f"  Retries: {total_retries}")
        self.logger.info(f"  Notion Published: {self.stats.get('notion_published', 0)}")
        self.logger.info(f"  Total Time: {total_time:.0f}ms")
        self.logger.info("=" * 50)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        return {
            **self.stats,
            'success_rate': (self.stats['successful'] / self.stats['total_executed'] * 100) 
                           if self.stats['total_executed'] > 0 else 0,
            'handlers': list(self.handlers.keys())
        }


# Need pandas for calculations
try:
    import pandas as pd
except ImportError:
    pd = None


# ==========================================
# STANDALONE TEST
# ==========================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("ExecutorTest")
    
    # Create mock config
    class MockConfig:
        OUTPUT_DIR = str(PROJECT_ROOT / "output")
    
    executor = TaskExecutor(MockConfig(), logger)
    
    print("\n=== Task Executor Test ===")
    print(f"Output directory: {executor.output_dir}")
    print(f"Research directory: {executor.research_dir}")
    print(f"Available handlers: {list(executor.handlers.keys())}")
