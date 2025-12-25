# Syndicate Android MVP

> Comprehensive Design Blueprint

---

## 1. **Technology Stack**

**Language:**
- Kotlin (entire codebase)

**Frameworks/Libraries:**
- Jetpack Compose (UI)
- Retrofit & OkHttp (network requests)
- Gson (JSON parsing)
- Room (local persistence)
- Hilt (Dependency Injection)
- MPAndroidChart (chart visualization)
- Android Navigation Component (in Compose)
- Coroutines + Flow/LiveData (async, data stream)
- Material 3 (theming/components)

**Minimum SDK:**
- 24 (Android 7.0 Nougat)

---

## 2. **Codebase Structure**

Organized for clarity, testing, and feature growth:

```
com/
└── goldstandard/
    ├── GoldStandardApp.kt
    ├── di/                      // Hilt modules
    ├── model/                   // Data classes (Price, Report, Indicator)
    ├── data/
    │     ├── network/           // APIs, DTOs
    │     ├── local/             // DAO, Room entities, AppDatabase
    │     ├── repository/        // Logic for data source coordination
    │     └── indicator/         // Indicator calculation utils (SMA, RSI)
    ├── ui/
    │     ├── dashboard/
    │     ├── chart/
    │     ├── reports/
    │     ├── navigation/
    │     └── theme/
    └── viewmodel/               // All VM classes
```

---

## 3. **Core Entity Models**

```kotlin
// model/Price.kt
data class Price(val timestamp: Long, val value: Float)

// model/Report.kt
@Entity(tableName = "reports")
data class Report(
    @PrimaryKey(autoGenerate = true) val id: Int = 0,
    val title: String,
    val date: Long,
    val content: String
)

// model/IndicatorValues.kt
data class IndicatorValues(val rsi: Float, val sma: Float)
```

---

## 4. **Networking Layer (data/network/)**

- **Market API:**
  - Use Yahoo Finance or Alpha Vantage
  - Example endpoint: `https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=1d&range=3mo`

- **Retrofit Service Example:**

```kotlin
interface GoldApiService {
    @GET("v8/finance/chart/GC=F")
    suspend fun getGoldChart(
        @Query("interval") interval: String = "1d",
        @Query("range") range: String = "3mo"
    ): GoldChartResponse
}
```

- **Parsing:**
  - Use Gson or Kotlin serialization for mapping JSON.

---

## 5. **Local Storage with Room (data/local/)**

- Define `ReportEntity`, `ReportDao`, and `AppDatabase`.

```kotlin
@Dao
interface ReportDao {
    @Query("SELECT * FROM reports ORDER BY date DESC")
    fun getAllReports(): Flow<List<Report>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(report: Report)
}
```

- Create `AppDatabase` as a singleton with Hilt.

---

## 6. **Repository Layer (data/repository/)**

Handles multi-source data ops (network & local):

```kotlin
@Singleton
class GoldRepository @Inject constructor(
    private val api: GoldApiService,
    private val reportDao: ReportDao
) {
    suspend fun getCurrentGoldPrice(): Float { ... }
    suspend fun getHistoricalPrices(): List<Price> { ... }
    suspend fun saveReport(report: Report) { ... }
    fun getReports(): Flow<List<Report>> = reportDao.getAllReports()
}
```

---

## 7. **Indicator Calculation (data/indicator/IndicatorUtils.kt)**

- Implement SMA and RSI in pure Kotlin.
- On price fetch, call these functions and return values to ViewModel.

---

## 8. **ViewModels (viewmodel/)**

- Each screen gets its own ViewModel.
- Hold UI state, interact with repositories, and expose data as StateFlow for Compose.

---

## 9. **UI Layer (ui/) with Jetpack Compose**

### **A. Navigation**
- Use Navigation Compose; define sealed routes for **Dashboard**, **Chart**, **Reports**, **ReportDetail**.

### **B. Screens**

1. **DashboardScreen**
    - Shows latest gold price, change %, fetch status
    - Refresh button
    - Navigation arrows/icons to Chart & Reports

2. **ChartScreen**
    - MPAndroidChart (via AndroidView in Compose)
    - Buttons/toggles to overlay SMA & RSI
    - Responsive to data state (loading, error)

3. **ReportsScreen**
    - LazyColumn of reports, showing title & formatted date
    - FAB to refresh or (in future) add report

4. **ReportDetailScreen**
    - Full markdown/plaintext render of the report, styled

5. **Theme**
    - Material 3 dark palette
    - Background: `#1a1a2e`
    - Accent: `#ffd700`
    - Charts: gold, blue, red overlays

### **C. Example Compose UI Fragment**

```kotlin
@Composable
fun DashboardScreen(state: DashboardState, onRefresh: () -> Unit, navToChart: () -> Unit, navToReports: () -> Unit) {
    Column(Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background)) {
        Text("Gold Price", style = MaterialTheme.typography.titleLarge, color = Color(0xFFFFD700))
        Text("$${state.price} (${state.changePercent}%)", style = MaterialTheme.typography.displayLarge)
        Button(onClick = onRefresh) { Text("Refresh") }
        Spacer(Modifier.height(16.dp))
        Row {
            IconButton(onClick = navToChart) { Icon(Icons.Default.ShowChart, contentDescription = "Chart") }
            IconButton(onClick = navToReports) { Icon(Icons.Default.List, contentDescription = "Reports") }
        }
        // ...loading & error UI
    }
}
```

---

## 10. **Chart Integration (ui/chart/GoldChart.kt)**

- Embed MPAndroidChart using `AndroidView` inside Compose.
- Provide chart with historical data and computed overlay series for SMA, RSI.

```kotlin
@Composable
fun GoldChart(prices: List<Price>, sma: List<Float>, rsi: List<Float>, modifier: Modifier) {
    AndroidView(factory = { ctx ->
        LineChart(ctx).apply {
            // Add entries for prices, SMA, RSI
        }
    }, modifier = modifier)
}
```

---

## 11. **Theming (ui/theme/Theme.kt)**

- Define dark and light ColorSchemes.
- Extend with gold/accent custom colors as needed.

---

## 12. **Dependency Injection: Hilt (di/)**

- Annotate your Application class (`@HiltAndroidApp`).
- Provide modules for Repository, ApiService, and Database singletons.

---

## 13. **Testing**

- Unit test indicator utils, Repository.
- Use `runBlockingTest` for coroutine-based ViewModels.
- Basic UI tests with Compose's testing API.

---

## 14. **Extensibility & Adaptation Guidance**

- **Add assets:** Modularize `model/Price.kt` so you can add support for Silver, Platinum later by parameterizing ticker and endpoints.
- **Add advanced indicators:** Place all indicator logic in a single module for future expansion (MACD, ATR, etc).
- **Add AI features:** Reserved space for API keys, design reports to be able to add “AI Analysis” sections.

---

## 15. **Development Milestone Checklist**

1. Project scaffold, theming, and navigation (Day 1–2)
2. Gold price fetch/display (Day 3–4)
3. Chart with overlays (Day 5–8)
4. Local Report storage, list, and details (Day 9–10)
5. Polishing, error handling, and UI/UX review (Day 11–12)
6. Testing and optimization (Day 13)
7. Adaptive refactor for easy future extensions (Day 14+)

---

## 16. **Flexible Practice**

- All critical business logic in ViewModel, never in UI.
- All data parsing/calc pure, single-responsibility, easy to swap out.
- Theme, navigation, data, and indicators trivially extendable.
- Every data layer is interface-driven for future remote/local/adaptive source changes.
- Charts/indicators/scalars all decoupled for rapid UI tweaks.

---
