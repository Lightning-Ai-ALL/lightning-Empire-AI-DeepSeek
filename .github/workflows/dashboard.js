// csv_utils.js - 主 CSV 處理工具（補全套）
function parseCSV(csvText) {
  const lines = csvText.trim().split('\n');
  const headers = lines[0].split(',').map(h => h.trim());
  const data = [];
  
  for (let i = 1; i < lines.length; i++) {
    if (!lines[i].trim()) continue;
    const values = lines[i].split(',').map(v => v.trim());
    const obj = {};
    headers.forEach((header, index) => {
      obj[header] = values[index] || '';
    });
    data.push(obj);
  }
  return { headers, data, columnCount: headers.length };
}

// 驗證 Schema
function validateSchema(parsed, expectedCols = 12) {
  if (parsed.columnCount !== expectedCols) {
    console.warn(`⚠️ Schema mismatch: ${parsed.columnCount} vs ${expectedCols}`);
    return false;
  }
  return true;
}

// 範例使用（dashboard.html 呼叫）
async function loadAndValidateCSV(url) {
  const res = await fetch(url);
  const text = await res.text();
  const parsed = parseCSV(text);
  const isValid = validateSchema(parsed);
  console.log("CSV Valid:", isValid, "| Columns:", parsed.columnCount);
  return parsed;
}
