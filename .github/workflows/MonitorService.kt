class MonitorService : Service() {
    private lateinit var aiCore: TFLitePredictor
    private lateinit var learner: OnlineLearner

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        aiCore = TFLitePredictor(this)
        learner = OnlineLearner()

        // 每 5 秒進行一次 NPU 推理
        fixedRateTimer("AI_CORE", true, 0L, 5000L) {
            val currentState = getSystemMetrics()
            val mode = aiCore.predict(currentState)
            
            if (mode == 2) { // 預測結果為：需要終極壓制
                MQTTClient.publish("home/ir/ac", "ULTRA_COOL_MODE")
                logToCSV(currentState, "AI_AUTO_AC_ON")
            }
        }
        return START_STICKY
    }
}

package com.eeis.ai.service

import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.BatteryManager
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import com.eeis.ai.ai.HybridAI
import com.eeis.ai.model.SystemState

class MonitorService : Service() {
    
    private val handler = Handler(Looper.getMainLooper())
    private var isMonitoring = false
    private val monitorRunnable = object : Runnable {
        override fun run() {
            if (isMonitoring) {
                val state = getSystemState()
                // 把當下狀態送入 AI 決策核心
                HybridAI.process(state) 
                handler.postDelayed(this, 3000) // 每 3 秒監控一次
            }
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        isMonitoring = true
        handler.post(monitorRunnable)
        return START_STICKY // 被系統殺掉後自動重啟
    }

    private fun getSystemState(): SystemState {
        val batteryManager = getSystemService(Context.BATTERY_SERVICE) as BatteryManager
        val battery = batteryManager.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY)
        
        // 取得 CPU 負載、溫度、訊號等 (需自行結合 Android 的 ActivityManager 與 SensorManager)
        // 這裡先寫簡化模擬值，實際專案需補上對應 API
        val cpuLoad = 50 // 模擬值
        val temp = 35   // 模擬值
        val signal = -90 // 模擬值

        return SystemState(battery, 70, cpuLoad, temp, signal)
    }

    override fun onBind(intent: Intent?): IBinder? = null
    
    override fun onDestroy() {
        super.onDestroy()
        isMonitoring = false
        handler.removeCallbacks(monitorRunnable)
    }
}
