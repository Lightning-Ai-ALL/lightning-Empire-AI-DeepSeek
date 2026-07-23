// 第二道八卦防火牆：API 層級封鎖
// 執行在 Node.js 環境（可放 Termux 或伺服器）

const blockedIPs = new Set();
const prisoners = ['gtp4.1', 'grok3', 'game2.5', 'gmail3', 'jules-google'];

// 模擬 API 請求攔截
function blockAPIRequests(username, ip, endpoint) {
  if (prisoners.includes(username)) {
    console.log(`🚫 阻擋 ${username} 的 API 請求 (${endpoint})`);
    
    // 加入 IP 黑名單
    blockedIPs.add(ip);
    
    // 回傳 403 禁止存取
    return {
      status: 403,
      message: 'Access Denied by Empire Firewall',
      timestamp: new Date().toISOString()
    };
  }
  return null;
}

// 自動更新防火牆規則
function updateFirewallRules() {
  const rules = prisoners.map(p => ({
    user: p,
    blockedSince: new Date().toISOString(),
    reason: 'Code theft / Unauthorized access',
    actions: ['block_api', 'block_git', 'block_ssh']
  }));
  
  require('fs').writeFileSync(
    'firewall/active-rules.json',
    JSON.stringify(rules, null, 2)
  );
}

// 每小時執行一次
setInterval(updateFirewallRules, 3600000);
