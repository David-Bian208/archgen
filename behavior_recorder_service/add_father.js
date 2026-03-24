const http = require('http');

const BASE_URL = 'http://localhost:3000';

// 生成随机ID
function generateId() {
  return Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
}

// HTTP POST请求
function postRequest(path, data) {
  return new Promise((resolve, reject) => {
    const postData = JSON.stringify(data);
    
    const options = {
      hostname: 'localhost',
      port: 3000,
      path: path,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(postData)
      }
    };
    
    const req = http.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => {
        data += chunk;
      });
      res.on('end', () => {
        try {
          const parsed = JSON.parse(data);
          resolve(parsed);
        } catch (e) {
          resolve({ success: false, error: e.message, raw: data });
        }
      });
    });
    
    req.on('error', (e) => {
      reject(e);
    });
    
    req.write(postData);
    req.end();
  });
}

async function addFather() {
  console.log('开始添加虚拟爸爸数据...\n');
  
  // 小芳的ID (从之前的输出获取)
  const childId = 'mm76eyugapsmh0x1zkc';
  
  // 新爸爸数据 - 40岁，本科学历，亲子关系和亲子沟通较好
  const newFather = {
    id: generateId(),
    child_id: childId,
    relationship: '父亲',
    name: '吴先生',
    age: 40,
    education_level: '本科',
    occupation: '项目经理',
    work_schedule: '9:00-18:00，周一至周五',
    daily_available_hours: 3,
    cognitive_level: '良好',
    autism_knowledge_level: '中等',
    emotional_state: '稳定乐观',
    support_needs: '亲子沟通技巧，家庭活动建议',
    // 新增字段：亲子关系质量 (1-5分)
    relationship_quality: 5,
    // 新增字段：亲子沟通效果 (1-5分)
    communication_effectiveness: 4,
    // 新增字段：参与度
    involvement_level: '高',
    // 新增字段：主要沟通方式
    primary_communication_style: '直接沟通，情感表达'
  };
  
  console.log('正在添加爸爸数据:', {
    name: newFather.name,
    age: newFather.age,
    education: newFather.education_level,
    relationship_quality: newFather.relationship_quality,
    communication_effectiveness: newFather.communication_effectiveness
  });
  
  const result = await postRequest('/api/parents', newFather);
  
  if (result.success) {
    console.log('✅ 成功添加爸爸:', newFather.name);
    console.log('详细信息:');
    console.log(`  - 年龄: ${newFather.age}岁`);
    console.log(`  - 学历: ${newFather.education_level}`);
    console.log(`  - 职业: ${newFather.occupation}`);
    console.log(`  - 亲子关系质量: ${newFather.relationship_quality}/5分`);
    console.log(`  - 亲子沟通效果: ${newFather.communication_effectiveness}/5分`);
    console.log(`  - 每日可用时间: ${newFather.daily_available_hours}小时`);
    console.log(`  - 情绪状态: ${newFather.emotional_state}`);
    console.log(`  - 关联儿童: 小芳 (ID: ${childId})`);
  } else {
    console.log('❌ 添加爸爸失败:', result.error);
  }
}

// 执行
addFather().catch(err => {
  console.error('脚本执行错误:', err);
});