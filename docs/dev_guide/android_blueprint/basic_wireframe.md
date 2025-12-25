# Syndicate Android MVP

> Conceptual Wireframes

---

## 1. **Navigation Structure**

Use a bottom navigation bar or top bar with the main sections:

```
+-----------------------------------------------+
|  Dashboard | Chart | Reports                  |
+-----------------------------------------------+
```

All main screens can be reached from this navigation.

---

## 2. **Wireframe: Dashboard Screen**

```
+--------------------------------------------------------------+
| Syndicate [Top App Bar, Title, Gold accent]              |
+--------------------------------------------------------------+
|   GOLD PRICE          [last updated: 14:32]      (Refresh)   |
|--------------------------------------------------------------|
|   $2,045.00         +1.23%  (↑)   [Gold color, bold]         |
|--------------------------------------------------------------|
|  [ Cards for quick stats: ]                                  |
|   ┌───────────────┐   ┌───────────────┐                      |
|   │  Weekly Trend │   │ Monthly Trend │                      |
|   │  +0.8%        │   │  +3.2%        │                      |
|   └───────────────┘   └───────────────┘                      |
|--------------------------------------------------------------|
|           [CHART]                 [REPORTS]                  |
|    (button or icon, prominent)    (button or icon)           |
+--------------------------------------------------------------+
|  [Loading/Network error banners as needed]                   |
+--------------------------------------------------------------+
| [Bottom Navigation Bar]                                      |
+--------------------------------------------------------------+
```

---

## 3. **Wireframe: Chart Screen**

```
+--------------------------------------------------------------+
| Chart [Top App Bar, back nav]                                |
+--------------------------------------------------------------+
|   Gold Price Chart   [range: 1m | 3m | 6m]                   |
|--------------------------------------------------------------|
| [MPAndroidChart: Candlesticks or Line]                       |
|   |   |   Candlesticks for dates                             |
|   |   |                                                     |
|   |   |   (Gold line=price; overlay line=RSI or SMA)         |
|--------------------------------------------------------------|
| [Indicators toggles: (checkbox)]                             |
|  ☐ Show RSI   ☐ Show SMA(50)                                 |
|--------------------------------------------------------------|
| [Legend, Axis labels, Gold-color for highlight]              |
+--------------------------------------------------------------+
| [Bottom Navigation Bar]                                      |
+--------------------------------------------------------------+
```

---

## 4. **Wireframe: Reports List Screen**

```
+--------------------------------------------------------------+
| Reports [Top App Bar, back nav]                              |
+--------------------------------------------------------------+
| [Search or filter if desired]                                |
|--------------------------------------------------------------|
| ▸ Daily Report (2025-11-25)                                  |
|    "Gold up on forecast optimism..."                         |
|--------------------------------------------------------------|
| ▸ Weekly Summary (2025-11-23)                                |
|    "Markets trend bullish with..."                           |
|--------------------------------------------------------------|
| ... (more report cards, scrollable)                          |
+--------------------------------------------------------------+
| [Bottom Navigation Bar]                                      |
+--------------------------------------------------------------+
```

---

## 5. **Wireframe: Report Detail Screen**

```
+--------------------------------------------------------------+
| Report Details [Top App Bar, back nav]                       |
+--------------------------------------------------------------+
| [Report title, date]                                         |
|  Daily Report (2025-11-25)                                   |
|--------------------------------------------------------------|
| [Markdown/plaintext content, styled]                         |
|  Today gold rose 1.2% due to ...                             |
|  ...                                                         |
|--------------------------------------------------------------|
| [Share Button] [Back Button]                                 |
+--------------------------------------------------------------+
```

---

## 6. **Wireframe: Loading/Network/Error States**

All main screens should support banners/toasts/snackbars for transient feedback:

```
---------------------------------------------------------------
| [!] Network Error: Please check your connection and retry.  |
---------------------------------------------------------------
| [↻ Loading data, please wait...]                            |
---------------------------------------------------------------
```

---

## 7. **Colors & Fonts**

- **Background**: #1a1a2e (Deep blue)
- **Accent**: #ffd700 (Gold)
- **Text**: #eaeaea (Primary), #a0a0a0 (Secondary/dim)
- **Charts**: Gold/accented lines/legend
- **Buttons**: Rounded, gold-outline for primary, flat for secondary

---

## 8. **Sample Navigation Flow**

```
Dashboard  →  Chart      [via nav bar or button]
              ↓
         Reports List
              ↓
         Report Detail
```

---

## 9. **Modular Component Wireframes**

- **Statistic Card**:  (for trends/week/month)
```
┌─────────────────────────┐
|   Weekly Trend          |
|   +0.8%                 |
└─────────────────────────┘
```

- **Chart Toggle**
```
[  ☐ Show RSI ]   [  ☐ Show SMA(50) ]
```

- **Report Card**
```
▸ [Title] (Date)
   [lead summary…]
```

---
