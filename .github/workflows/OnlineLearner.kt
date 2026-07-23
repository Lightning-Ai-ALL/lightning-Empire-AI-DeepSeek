class OnlineLearner {
    private val weights = mutableMapOf("user_preference" to 1.0f)

    fun learnFromUser(action: String, state: SystemState) {
        // 如果你在高溫時手動開啟冷氣，AI 會增加「溫度」在決策中的權重
        if (action == "MANUAL_AC_ON" && state.temp > 40) {
            weights["temp_sensitivity"] = weights.getOrDefault("temp_sensitivity", 1.0f) + 0.1f
        }
    }

    fun adjust(prediction: Int): Int {
        // 根據權重修正 TFLite 的原始輸出，達成「人機合一」
        return prediction // 實作邏輯：權重乘法修正
    }
}
