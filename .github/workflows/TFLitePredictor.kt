class TFLitePredictor(context: Context) {
    private var interpreter: Interpreter? = null

    init {
        val options = Interpreter.Options().apply {
            // 關鍵：強制使用 NNAPI 以啟動 8 Elite NPU 加速
            setUseNNAPI(true)
            setNumThreads(4)
        }
        val model = loadModelFile(context, "mode_predictor.tflite")
        interpreter = Interpreter(model, options)
    }

    fun predict(state: SystemState): Int {
        val input = arrayOf(floatArrayOf(
            state.battery / 100f,
            state.ram / 100f,
            state.cpuLoad / 100f,
            state.temp / 60f,
            (state.signal + 120) / 70f
        ))
        val output = Array(1) { FloatArray(3) }
        interpreter?.run(input, output)
        
        // 返回機率最高的模式索引
        return output[0].indices.maxByOrNull { output[0][it] } ?: 0
    }
}

