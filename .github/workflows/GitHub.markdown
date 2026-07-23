# EEIS / 系統控制中心 v4（TFLite 真 AI 完整架構）

> 這是一份完整的工程級升級包設計，可直接用於 Android Studio 專案。

## 包含四大核心組件
- ✅ UI（Compose + XML 雙模式）
- ✅ TFLite 可訓練模型模板與推論引擎
- ✅ 省電 AI 規則引擎 + Hybrid AI（人機共治）
- ✅ 一鍵 APK 架構（Gradle + build flow）

---

## 📱 1. UI 系統（Compose + XML 雙模式）

### 🟢 Compose 版本（推薦）
```kotlin
@Composable
fun ControlCenterScreen(viewModel: MainViewModel) {
    val state by viewModel.state.collectAsState()
    Column {
        Text("AI Control Center")
        Card {
            Text("Battery: ${state.battery}%")
            Text("CPU: ${state.cpu}%")
            Text("Temp: ${state.temp}")
        }
        Button(onClick = { viewModel.runAI() }) {
            Text("Run AI Optimize")
        }
        when (state.mode) {
            "SAVE" -> Text("省電模式")
            "ULTRA" -> Text("極限省電")
            else -> Text("效能模式")
        }
    }
}
