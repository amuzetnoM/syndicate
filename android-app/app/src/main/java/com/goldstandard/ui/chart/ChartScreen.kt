package com.goldstandard.ui.chart

import android.graphics.Color as AndroidColor
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.hilt.navigation.compose.hiltViewModel
import com.github.mikephil.charting.charts.LineChart
import com.github.mikephil.charting.components.XAxis
import com.github.mikephil.charting.data.Entry
import com.github.mikephil.charting.data.LineData
import com.github.mikephil.charting.data.LineDataSet
import com.goldstandard.R
import com.goldstandard.model.Price
import com.goldstandard.ui.theme.ChartBlue
import com.goldstandard.ui.theme.ChartRed
import com.goldstandard.ui.theme.Gold
import com.goldstandard.viewmodel.ChartState
import com.goldstandard.viewmodel.ChartViewModel
import java.text.DecimalFormat

/**
 * Chart screen displaying historical gold prices with indicator overlays.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChartScreen(
    onNavigateBack: () -> Unit,
    viewModel: ChartViewModel = hiltViewModel()
) {
    val state by viewModel.state.collectAsState()
    
    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = stringResource(R.string.chart_title),
                        color = Gold
                    )
                },
                navigationIcon = {
                    IconButton(onClick = onNavigateBack) {
                        Icon(
                            imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = stringResource(R.string.content_description_back),
                            tint = MaterialTheme.colorScheme.onSurface
                        )
                    }
                },
                actions = {
                    IconButton(onClick = { viewModel.refresh() }) {
                        Icon(
                            imageVector = Icons.Default.Refresh,
                            contentDescription = stringResource(R.string.refresh),
                            tint = Gold
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.background
                )
            )
        }
    ) { paddingValues ->
        ChartContent(
            state = state,
            onToggleSMA = { viewModel.toggleSMA() },
            onToggleRSI = { viewModel.toggleRSI() },
            onRangeChange = { viewModel.setRange(it) },
            modifier = Modifier.padding(paddingValues)
        )
    }
}

@Composable
private fun ChartContent(
    state: ChartState,
    onToggleSMA: () -> Unit,
    onToggleRSI: () -> Unit,
    onRangeChange: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    val percentFormat = DecimalFormat("0.00")
    
    Column(
        modifier = modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .padding(16.dp)
    ) {
        // Range Selection
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceEvenly
        ) {
            listOf("1mo", "3mo", "6mo", "1y").forEach { range ->
                FilterChip(
                    selected = state.selectedRange == range,
                    onClick = { onRangeChange(range) },
                    label = { Text(range.uppercase()) },
                    colors = FilterChipDefaults.filterChipColors(
                        selectedContainerColor = Gold,
                        selectedLabelColor = Color.Black
                    )
                )
            }
        }
        
        Spacer(modifier = Modifier.height(16.dp))
        
        // Indicator Toggles
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            FilterChip(
                selected = state.showSMA,
                onClick = onToggleSMA,
                label = { Text(stringResource(R.string.sma_overlay)) },
                colors = FilterChipDefaults.filterChipColors(
                    selectedContainerColor = ChartBlue,
                    selectedLabelColor = Color.White
                )
            )
            
            FilterChip(
                selected = state.showRSI,
                onClick = onToggleRSI,
                label = { Text(stringResource(R.string.rsi_overlay)) },
                colors = FilterChipDefaults.filterChipColors(
                    selectedContainerColor = ChartRed,
                    selectedLabelColor = Color.White
                )
            )
        }
        
        Spacer(modifier = Modifier.height(16.dp))
        
        // Indicator Values Card
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.surface
            )
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp),
                horizontalArrangement = Arrangement.SpaceAround
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(
                        text = "RSI (14)",
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                    )
                    Text(
                        text = percentFormat.format(state.indicators.rsi),
                        style = MaterialTheme.typography.titleLarge,
                        color = when {
                            state.indicators.rsi > 70 -> ChartRed
                            state.indicators.rsi < 30 -> ChartBlue
                            else -> MaterialTheme.colorScheme.onSurface
                        }
                    )
                }
                
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(
                        text = "SMA (14)",
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                    )
                    Text(
                        text = "$${percentFormat.format(state.indicators.sma)}",
                        style = MaterialTheme.typography.titleLarge,
                        color = ChartBlue
                    )
                }
            }
        }
        
        Spacer(modifier = Modifier.height(16.dp))
        
        // Chart
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .weight(1f),
            contentAlignment = Alignment.Center
        ) {
            if (state.isLoading) {
                CircularProgressIndicator(
                    modifier = Modifier.size(48.dp),
                    color = Gold
                )
            } else if (state.error != null) {
                Text(
                    text = state.error,
                    style = MaterialTheme.typography.bodyLarge,
                    color = MaterialTheme.colorScheme.error
                )
            } else if (state.prices.isNotEmpty()) {
                GoldChart(
                    prices = state.prices,
                    smaSeries = if (state.showSMA) state.smaSeries else emptyList(),
                    rsiSeries = if (state.showRSI) state.rsiSeries else emptyList(),
                    modifier = Modifier.fillMaxSize()
                )
            }
        }
    }
}

/**
 * Composable wrapper for MPAndroidChart LineChart.
 */
@Composable
fun GoldChart(
    prices: List<Price>,
    smaSeries: List<Float>,
    rsiSeries: List<Float>,
    modifier: Modifier = Modifier
) {
    val goldColor = Gold.toArgb()
    val blueColor = ChartBlue.toArgb()
    val redColor = ChartRed.toArgb()
    val backgroundColor = MaterialTheme.colorScheme.background.toArgb()
    val textColor = MaterialTheme.colorScheme.onSurface.toArgb()
    
    AndroidView(
        factory = { context ->
            LineChart(context).apply {
                description.isEnabled = false
                setBackgroundColor(backgroundColor)
                legend.textColor = textColor
                legend.isEnabled = true
                
                // X Axis
                xAxis.apply {
                    position = XAxis.XAxisPosition.BOTTOM
                    this.textColor = textColor
                    setDrawGridLines(false)
                    granularity = 1f
                }
                
                // Y Axis (Left)
                axisLeft.apply {
                    this.textColor = textColor
                    setDrawGridLines(true)
                    gridColor = AndroidColor.GRAY
                }
                
                // Y Axis (Right) - for RSI
                axisRight.apply {
                    this.textColor = textColor
                    setDrawGridLines(false)
                    axisMinimum = 0f
                    axisMaximum = 100f
                    isEnabled = rsiSeries.isNotEmpty()
                }
                
                setTouchEnabled(true)
                isDragEnabled = true
                setScaleEnabled(true)
                setPinchZoom(true)
            }
        },
        update = { chart ->
            val dataSets = mutableListOf<LineDataSet>()
            
            // Price data
            val priceEntries = prices.mapIndexed { index, price ->
                Entry(index.toFloat(), price.value)
            }
            
            val priceDataSet = LineDataSet(priceEntries, "Gold Price").apply {
                color = goldColor
                valueTextColor = textColor
                lineWidth = 2f
                setDrawCircles(false)
                setDrawValues(false)
                mode = LineDataSet.Mode.CUBIC_BEZIER
            }
            dataSets.add(priceDataSet)
            
            // SMA data
            if (smaSeries.isNotEmpty()) {
                val smaOffset = prices.size - smaSeries.size
                val smaEntries = smaSeries.mapIndexed { index, value ->
                    Entry((index + smaOffset).toFloat(), value)
                }
                
                val smaDataSet = LineDataSet(smaEntries, "SMA (14)").apply {
                    color = blueColor
                    valueTextColor = textColor
                    lineWidth = 1.5f
                    setDrawCircles(false)
                    setDrawValues(false)
                    mode = LineDataSet.Mode.CUBIC_BEZIER
                    enableDashedLine(10f, 5f, 0f)
                }
                dataSets.add(smaDataSet)
            }
            
            // RSI data (on secondary axis)
            if (rsiSeries.isNotEmpty()) {
                chart.axisRight.isEnabled = true
                
                // Scale RSI to match price range for visibility
                val rsiOffset = prices.size - rsiSeries.size - 1
                val rsiEntries = rsiSeries.mapIndexed { index, value ->
                    Entry((index + rsiOffset).toFloat(), value)
                }
                
                val rsiDataSet = LineDataSet(rsiEntries, "RSI (14)").apply {
                    color = redColor
                    valueTextColor = textColor
                    lineWidth = 1.5f
                    setDrawCircles(false)
                    setDrawValues(false)
                    mode = LineDataSet.Mode.CUBIC_BEZIER
                    axisDependency = com.github.mikephil.charting.components.YAxis.AxisDependency.RIGHT
                }
                dataSets.add(rsiDataSet)
            } else {
                chart.axisRight.isEnabled = false
            }
            
            chart.data = LineData(dataSets.toList())
            chart.invalidate()
        },
        modifier = modifier
    )
}
