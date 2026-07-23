// ============================================
// 🧠 migrate.js - 配置迁移助手
// 从 main.yml 或 .env 读取核心设定，同步到各模块
// ============================================

const fs = require('fs');
const path = require('path');

// 主控配置路径（电脑版核心）
const MAIN_CONFIG = "D:/Lightning-ALL/.env";

function migrate() {
    console.log("🔄 开始迁移主权AI配置...");
    if (fs.existsSync(MAIN_CONFIG)) {
        const envContent = fs.readFileSync(MAIN_CONFIG, 'utf8');
        // 解析并写入本地 .env
        fs.writeFileSync('.env', envContent);
        console.log("✅ 已从电脑版核心同步环境变量");
    } else {
        console.log("⚠️ 未找到电脑版核心配置，使用默认值");
        // 默认配置：风能 API、霹雳车参数等
        const defaults = `
WEATHER_API_KEY=your_key_here
GROK_API_KEY=your_key_here
DISPATCH_MODE=disabled
PROFIT_MODE=wind_power
`;
        fs.writeFileSync('.env', defaults);
    }
    console.log("🎯 迁移完成，所有模块将遵循 main.yml 的主控逻辑");
}

migrate();


// distribute.js
const { ethers } = require("ethers");
const fs = require('fs');

// 設定
const provider = new ethers.providers.JsonRpcProvider("https://mainnet.infura.io/v3/YOUR_KEY");
const vaultAddress = "0xYourContractAddress";
const vaultABI = [ /* 合約ABI */ ];
const vault = new ethers.Contract(vaultAddress, vaultABI, provider);

// 分潤配置
const profitConfig = {
    aiWallet: "0xAI平台錢包地址",
    empireWallet: "0x帝國創建者錢包",
    members: [
        { address: "0x成員1", amount: 10000 },
        { address: "0x成員2", amount: 10000 }
    ]
};

async function distribute(totalAmount) {
    // 計算各項金額
    const aiShare = Math.floor(totalAmount * 0.7);
    const empireShare = Math.floor(totalAmount * 0.3);
    const memberTotal = profitConfig.members.reduce((s, m) => s + m.amount, 0);
    const remaining = totalAmount - aiShare - empireShare - memberTotal;

    const recipients = [
        profitConfig.aiWallet,
        profitConfig.empireWallet,
        ...profitConfig.members.map(m => m.address)
    ];
    const amounts = [
        aiShare,
        empireShare,
        ...profitConfig.members.map(m => m.amount)
    ];

    // 呼叫合約分潤
    const signer = new ethers.Wallet("YOUR_PRIVATE_KEY", provider);
    const vaultWithSigner = vault.connect(signer);
    const tx = await vaultWithSigner.distributeProfit(recipients, amounts, totalAmount);
    await tx.wait();

    // 記錄
    const receipt = {
        txHash: tx.hash,
        totalAmount,
        aiShare,
        empireShare,
        members: profitConfig.members,
        timestamp: new Date().toISOString(),
        merkle: ethers.utils.id(tx.hash).substring(2, 18)
    };
    fs.writeFileSync(`receipts/${Date.now()}.json`, JSON.stringify(receipt, null, 2));
    console.log("✅ 分潤完成", receipt);
}

// 讀取當前鎖定總額
async function main() {
    const totalLocked = await vault.getTotalLocked();
    console.log(`當前鎖定總額: ${ethers.utils.formatUnits(totalLocked, 6)} USDC`);
    // 假設要分潤全部
    await distribute(totalLocked);
}

main().catch(console.error);
