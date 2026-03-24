#!/usr/bin/env node

const http = require('http');

const BASE_URL = 'http://localhost:3000';

// 获取所有行为记录
function getAllRecords() {
  return new Promise((resolve, reject) => {
    http.get(`${BASE_URL}/api/records?limit=1000`, (res) => {
      let data = '';
      res.on('data', (chunk) => {
        data += chunk;
      });
      res.on('end', () => {
        try {
          const parsed = JSON.parse(data);
          if (parsed.success) {
            resolve(parsed.records);
          } else {
            reject(new Error(parsed.error || '获取记录失败'));
          }
        } catch (e) {
          reject(e);
        }
      });
    }).on('error', reject);
  });
}

// 获取所有儿童
function getAllChildren() {
  return new Promise((resolve, reject) => {
    http.get(`${BASE_URL}/api/children`, (res) => {
      let data = '';
      res.on('data', (chunk) => {
        data += chunk;
      });
      res.on('end', () => {
        try {
          const parsed = JSON.parse(data);
          if (parsed.success) {
            resolve(parsed.children);
          } else {
            reject(new Error(parsed.error || '获取儿童失败'));
          }
        } catch (e) {
          reject(e);
        }
      });
    }).on('error', reject);
  });
}

async function analyzeABCData() {
  console.log('=== ABC数据分析报告 ===\n');
  
  try {
    const records = await getAllRecords();
    const children = await getAllChildren();
    
    console.log(`数据统计:`);
    console.log(`- 儿童数量: ${children.length} 名`);
    console.log(`- 行为记录: ${records.length} 条\n`);
    
    // 按儿童分组
    const recordsByChild = {};
    const childMap = {};
    
    children.forEach(child => {
      childMap[child.id] = child.name;
      recordsByChild[child.id] = [];
    });
    
    records.forEach(record => {
      if (recordsByChild[record.child_id]) {
        recordsByChild[record.child_id].push(record);
      }
    });
    
    console.log('按儿童统计行为记录:');
    for (const [childId, childRecords] of Object.entries(recordsByChild)) {
      const childName = childMap[childId] || '未知儿童';
      console.log(`  ${childName}: ${childRecords.length} 条记录`);
    }
    console.log('');
    
    // ABC频率分析
    console.log('ABC频率分析:');
    
    // 前因频率
    const antecedentCount = {};
    const behaviorCount = {};
    const consequenceCount = {};
    const behaviorTypeCount = {};
    
    records.forEach(record => {
      // 前因
      const antecedent = record.abc_antecedent || '未记录';
      antecedentCount[antecedent] = (antecedentCount[antecedent] || 0) + 1;
      
      // 行为
      const behavior = record.abc_behavior || '未记录';
      behaviorCount[behavior] = (behaviorCount[behavior] || 0) + 1;
      
      // 后果
      const consequence = record.abc_consequence || '未记录';
      consequenceCount[consequence] = (consequenceCount[consequence] || 0) + 1;
      
      // 行为类型
      const type = record.behavior_type || '未分类';
      behaviorTypeCount[type] = (behaviorTypeCount[type] || 0) + 1;
    });
    
    // 显示前5个最常见的前因
    console.log('\n最常见的前因（触发因素）:');
    const topAntecedents = Object.entries(antecedentCount)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5);
    
    topAntecedents.forEach(([antecedent, count], index) => {
      const percentage = ((count / records.length) * 100).toFixed(1);
      console.log(`  ${index + 1}. ${antecedent}: ${count} 次 (${percentage}%)`);
    });
    
    // 显示前5个最常见的行为
    console.log('\n最常见的行为:');
    const topBehaviors = Object.entries(behaviorCount)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5);
    
    topBehaviors.forEach(([behavior, count], index) => {
      const percentage = ((count / records.length) * 100).toFixed(1);
      console.log(`  ${index + 1}. ${behavior}: ${count} 次 (${percentage}%)`);
    });
    
    // 显示前5个最常见的后果
    console.log('\n最常见的后果（处理方式）:');
    const topConsequences = Object.entries(consequenceCount)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5);
    
    topConsequences.forEach(([consequence, count], index) => {
      const percentage = ((count / records.length) * 100).toFixed(1);
      console.log(`  ${index + 1}. ${consequence}: ${count} 次 (${percentage}%)`);
    });
    
    // 行为类型分布
    console.log('\n行为类型分布:');
    for (const [type, count] of Object.entries(behaviorTypeCount)) {
      const percentage = ((count / records.length) * 100).toFixed(1);
      console.log(`  ${type}: ${count} 条 (${percentage}%)`);
    }
    
    // ABC链分析（前因→行为→后果的常见组合）
    console.log('\n常见ABC链（前因→行为→后果）:');
    const abcChains = {};
    
    records.forEach(record => {
      const chain = `${record.abc_antecedent || '未记录'} → ${record.abc_behavior || '未记录'} → ${record.abc_consequence || '未记录'}`;
      abcChains[chain] = (abcChains[chain] || 0) + 1;
    });
    
    const topChains = Object.entries(abcChains)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5);
    
    topChains.forEach(([chain, count], index) => {
      console.log(`  ${index + 1}. ${chain}: ${count} 次`);
    });
    
    // 情绪等级分析
    console.log('\n情绪等级分布 (1-5分，1=平静，5=失控):');
    const emotionLevels = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0};
    let totalEmotion = 0;
    let emotionSum = 0;
    
    records.forEach(record => {
      if (record.emotion_level) {
        emotionLevels[record.emotion_level] = (emotionLevels[record.emotion_level] || 0) + 1;
        totalEmotion++;
        emotionSum += record.emotion_level;
      }
    });
    
    for (let level = 1; level <= 5; level++) {
      const count = emotionLevels[level] || 0;
      const percentage = totalEmotion > 0 ? ((count / totalEmotion) * 100).toFixed(1) : '0.0';
      console.log(`  等级 ${level}: ${count} 次 (${percentage}%)`);
    }
    
    if (totalEmotion > 0) {
      const avgEmotion = (emotionSum / totalEmotion).toFixed(2);
      console.log(`  平均情绪等级: ${avgEmotion}`);
    }
    
    // 时间模式分析（按小时）
    console.log('\n行为发生时间分布（按小时）:');
    const hourDistribution = Array(24).fill(0);
    
    records.forEach(record => {
      if (record.timestamp) {
        const date = new Date(record.timestamp);
        const hour = date.getHours();
        hourDistribution[hour]++;
      }
    });
    
    // 显示高峰时段
    const maxCount = Math.max(...hourDistribution);
    const peakHours = hourDistribution
      .map((count, hour) => ({ hour, count }))
      .filter(item => item.count > 0)
      .sort((a, b) => b.count - a.count)
      .slice(0, 5);
    
    peakHours.forEach((item, index) => {
      const hourStr = `${item.hour}:00-${item.hour + 1}:00`;
      const percentage = ((item.count / records.length) * 100).toFixed(1);
      console.log(`  ${index + 1}. ${hourStr}: ${item.count} 次 (${percentage}%)`);
    });
    
    // 环境上下文分析
    console.log('\n环境上下文分布:');
    const contextCount = {};
    
    records.forEach(record => {
      const context = record.context || '未记录';
      contextCount[context] = (contextCount[context] || 0) + 1;
    });
    
    for (const [context, count] of Object.entries(contextCount)) {
      const percentage = ((count / records.length) * 100).toFixed(1);
      console.log(`  ${context}: ${count} 次 (${percentage}%)`);
    }
    
    console.log('\n=== 分析完成 ===');
    console.log('\n后续分析建议:');
    console.log('1. 深入分析特定ABC链的干预效果');
    console.log('2. 跟踪行为频率随时间的变化趋势');
    console.log('3. 比较不同后果策略的有效性');
    console.log('4. 识别高风险时段和环境，制定预防策略');
    
  } catch (error) {
    console.error('分析失败:', error.message);
  }
}

analyzeABCData();