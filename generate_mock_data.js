#!/usr/bin/env node

const http = require('http');

const BASE_URL = 'http://localhost:3000';

// 生成随机ID
function generateId() {
  return Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
}

// HTTP请求辅助函数
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

// 模拟数据
const mockChildren = [
  {
    id: generateId(),
    name: '小明',
    nickname: '明明',
    birth_date: '2019-06-15',
    gender: '男',
    diagnosis_date: '2023-03-10',
    diagnosis_source: '医院诊断',
    diagnosis_details: 'ASD Level 2，社交沟通障碍，刻板行为',
    current_symptoms: '语言发育迟缓，缺乏眼神接触，重复摇晃身体，对特定声音敏感',
    medical_history: '无重大疾病史，过敏：无',
    family_history: '舅舅有自闭症倾向',
    strengths: '记忆力强，对数字敏感，喜欢拼图',
    challenges: '社交互动困难，情绪调节障碍，语言表达有限',
    reinforcers: '小熊饼干，小汽车玩具，音乐',
    interests: '数字，拼图，火车，旋转物体',
    communication_preferences: '使用图片交换系统，简短指令',
    sensory_preferences: '不喜欢嘈杂声音，喜欢深压力拥抱'
  },
  {
    id: generateId(),
    name: '小芳',
    nickname: '芳芳',
    birth_date: '2018-09-22',
    gender: '女',
    diagnosis_date: '2022-11-05',
    diagnosis_source: '医院诊断',
    diagnosis_details: 'ASD Level 1，高功能自闭症',
    current_symptoms: '社交动机弱，对话技巧有限，兴趣狭窄',
    medical_history: '早产（35周），轻度哮喘',
    family_history: '无相关病史',
    strengths: '阅读能力强，识字早，绘画天赋',
    challenges: '理解他人情感困难，过渡困难，焦虑情绪',
    reinforcers: '贴纸，彩色笔，故事书',
    interests: '绘画，读书，恐龙，公主故事',
    communication_preferences: '直接明确的指令，视觉提示',
    sensory_preferences: '不喜欢黏腻触感，喜欢毛绒玩具'
  },
  {
    id: generateId(),
    name: '小强',
    nickname: '强强',
    birth_date: '2020-03-10',
    gender: '男',
    diagnosis_date: '2024-01-20',
    diagnosis_source: '医院诊断',
    diagnosis_details: 'ASD Level 3，需要高强度支持',
    current_symptoms: '无功能性语言，自伤行为，严重社交回避',
    medical_history: '癫痫史（控制良好）',
    family_history: '表兄有发育迟缓',
    strengths: '运动协调能力好，节奏感强',
    challenges: '沟通障碍，行为问题，自理能力有限',
    reinforcers: '摇摆椅，振动玩具，特定音乐',
    interests: '旋转物体，灯光，水',
    communication_preferences: '手势沟通，AAC设备',
    sensory_preferences: '寻求前庭刺激，喜欢摇摆'
  }
];

const mockParents = [
  // 小明的家长
  {
    id: generateId(),
    child_id: '', // 将在运行时填充
    relationship: '父亲',
    name: '张先生',
    age: 38,
    education_level: '本科',
    occupation: '工程师',
    work_schedule: '9:00-18:00，周一至周五',
    daily_available_hours: 2.5,
    cognitive_level: '良好',
    autism_knowledge_level: '中等',
    emotional_state: '有时焦虑，但总体积极',
    support_needs: '行为管理技巧，情绪调节策略'
  },
  {
    id: generateId(),
    child_id: '', // 将在运行时填充
    relationship: '母亲',
    name: '李女士',
    age: 35,
    education_level: '硕士',
    occupation: '教师',
    work_schedule: '8:00-16:00，周一至周五',
    daily_available_hours: 4,
    cognitive_level: '优秀',
    autism_knowledge_level: '良好',
    emotional_state: '压力较大，但学习能力强',
    support_needs: '家校合作策略，减压方法'
  },
  // 小芳的家长
  {
    id: generateId(),
    child_id: '', // 将在运行时填充
    relationship: '母亲',
    name: '王女士',
    age: 32,
    education_level: '本科',
    occupation: '设计师',
    work_schedule: '灵活，可在家工作',
    daily_available_hours: 6,
    cognitive_level: '良好',
    autism_knowledge_level: '基础',
    emotional_state: '有耐心，但缺乏专业知识',
    support_needs: '教育干预方法，社交技能训练'
  },
  {
    id: generateId(),
    child_id: '', // 将在运行时填充
    relationship: '父亲',
    name: '刘先生',
    age: 36,
    education_level: '大专',
    occupation: '销售经理',
    work_schedule: '经常出差',
    daily_available_hours: 1.5,
    cognitive_level: '中等',
    autism_knowledge_level: '新手',
    emotional_state: '困惑，需要指导',
    support_needs: '基础自闭症知识，简单干预技巧'
  },
  // 小强的家长
  {
    id: generateId(),
    child_id: '', // 将在运行时填充
    relationship: '母亲',
    name: '陈女士',
    age: 40,
    education_level: '高中',
    occupation: '全职照顾孩子',
    work_schedule: '全天',
    daily_available_hours: 8,
    cognitive_level: '基础',
    autism_knowledge_level: '中等',
    emotional_state: '疲惫，但坚定',
    support_needs: '喘息服务，行为危机处理'
  },
  {
    id: generateId(),
    child_id: '', // 将在运行时填充
    relationship: '父亲',
    name: '赵先生',
    age: 42,
    education_level: '本科',
    occupation: '个体经营',
    work_schedule: '时间灵活',
    daily_available_hours: 3,
    cognitive_level: '中等',
    autism_knowledge_level: '基础',
    emotional_state: '担忧经济压力',
    support_needs: '经济补助信息，社区资源'
  }
];

const mockProfessionals = [
  {
    id: generateId(),
    child_id: '', // 将在运行时填充
    type: '康复机构',
    name: '阳光康复中心',
    contact_info: '13800138000，北京市朝阳区',
    qualification: '三级康复机构',
    experience_years: 8,
    treatment_approach: 'ABA，感统训练，言语治疗',
    session_frequency: '每周3次',
    session_duration: '每次2小时',
    notes: '提供一对一训练和小组课程'
  },
  {
    id: generateId(),
    child_id: '', // 将在运行时填充
    type: '医院',
    name: '市儿童医院发育行为科',
    contact_info: '010-12345678，北京市西城区',
    qualification: '三甲医院',
    experience_years: 15,
    treatment_approach: '综合干预，药物治疗评估',
    session_frequency: '每月1次',
    session_duration: '每次1小时',
    notes: '主治医师：李医生，擅长自闭症诊断和干预'
  },
  {
    id: generateId(),
    child_id: '', // 将在运行时填充
    type: '特教学校',
    name: '希望特殊教育学校',
    contact_info: '13900139000，北京市海淀区',
    qualification: '市级特教示范学校',
    experience_years: 12,
    treatment_approach: '结构化教学，TEACCH',
    session_frequency: '每天',
    session_duration: '6小时/天',
    notes: '提供全日制特殊教育，师生比1:3'
  }
];

// ABC行为记录模板
const abcTemplates = [
  {
    antecedent: '要求完成任务',
    behavior: '哭闹、扔东西',
    consequence: '暂停任务，给予安抚',
    type: '问题行为',
    contexts: ['家里', '学校', '训练机构']
  },
  {
    antecedent: '想要玩具被拒绝',
    behavior: '躺在地上尖叫',
    consequence: '转移注意力，给予替代物',
    type: '问题行为',
    contexts: ['家里', '公共场所']
  },
  {
    antecedent: '听到巨大噪音',
    behavior: '捂住耳朵，躲藏',
    consequence: '带到安静环境，提供降噪耳机',
    type: '感官敏感',
    contexts: ['公共场所', '家里']
  },
  {
    antecedent: '看到喜欢的食物',
    behavior: '用手指，说"要"',
    consequence: '立即给予食物并表扬',
    type: '沟通行为',
    contexts: ['家里', '餐厅']
  },
  {
    antecedent: '转换活动（如结束游戏）',
    behavior: '抗拒，说"不要"',
    consequence: '使用视觉提示，给予过渡时间',
    type: '过渡困难',
    contexts: ['家里', '学校', '机构']
  },
  {
    antecedent: '与他人互动邀请',
    behavior: '转身离开，避免眼神接触',
    consequence: '不强迫，给予空间',
    type: '社交回避',
    contexts: ['学校', '公园', '家庭聚会']
  },
  {
    antecedent: '完成拼图任务',
    behavior: '微笑，拍手',
    consequence: '给予表扬和强化物',
    type: '积极行为',
    contexts: ['家里', '训练机构']
  },
  {
    antecedent: '等待轮次',
    behavior: '安静等待，看计时器',
    consequence: '及时轮到并给予强化',
    type: '自我调节',
    contexts: ['学校', '游戏小组']
  }
];

// 情绪等级描述
const emotionLevels = [
  { level: 1, desc: '平静，专注' },
  { level: 2, desc: '轻微不安' },
  { level: 3, desc: '中度焦虑' },
  { level: 4, desc: '明显激动' },
  { level: 5, desc: '极度激动，失控' }
];

async function generateMockData() {
  console.log('开始生成模拟数据...\n');
  
  // 1. 创建儿童
  console.log('创建儿童数据...');
  const childIds = [];
  for (const child of mockChildren) {
    const result = await postRequest('/api/children', child);
    if (result.success) {
      childIds.push(child.id);
      console.log(`  ✓ 创建儿童: ${child.name} (ID: ${child.id})`);
    } else {
      console.log(`  ✗ 创建儿童失败: ${child.name}`, result.error);
    }
  }
  
  // 2. 创建家长（关联儿童）
  console.log('\n创建家长数据...');
  let parentIndex = 0;
  const parentIds = [];
  
  for (let i = 0; i < childIds.length; i++) {
    // 每个儿童关联2位家长
    for (let j = 0; j < 2; j++) {
      if (parentIndex < mockParents.length) {
        const parent = { ...mockParents[parentIndex] };
        parent.child_id = childIds[i];
        
        const result = await postRequest('/api/parents', parent);
        if (result.success) {
          parentIds.push(parent.id);
          console.log(`  ✓ 创建家长: ${parent.name} (${parent.relationship}) 关联儿童: ${mockChildren[i].name}`);
        } else {
          console.log(`  ✗ 创建家长失败: ${parent.name}`, result.error);
        }
        parentIndex++;
      }
    }
  }
  
  // 3. 创建专业机构（每个儿童关联1-2个机构）
  console.log('\n创建专业机构数据...');
  const professionalIds = [];
  
  for (let i = 0; i < childIds.length; i++) {
    const childId = childIds[i];
    // 每个儿童关联1-2个机构
    const numProfessionals = Math.min(2, mockProfessionals.length);
    
    for (let j = 0; j < numProfessionals; j++) {
      const professional = { ...mockProfessionals[j] };
      professional.child_id = childId;
      
      const result = await postRequest('/api/professionals', professional);
      if (result.success) {
        professionalIds.push(professional.id);
        console.log(`  ✓ 创建机构: ${professional.name} 关联儿童: ${mockChildren[i].name}`);
      } else {
        console.log(`  ✗ 创建机构失败: ${professional.name}`, result.error);
      }
    }
  }
  
  // 4. 创建行为记录（ABC格式）
  console.log('\n创建行为记录数据（ABC格式）...');
  let totalRecords = 0;
  
  for (let childIdx = 0; childIdx < childIds.length; childIdx++) {
    const childId = childIds[childIdx];
    const childName = mockChildren[childIdx].name;
    const recordsPerChild = 15; // 每个儿童15条记录
    
    console.log(`  为 ${childName} 生成 ${recordsPerChild} 条行为记录...`);
    
    for (let i = 0; i < recordsPerChild; i++) {
      // 随机选择模板
      const template = abcTemplates[Math.floor(Math.random() * abcTemplates.length)];
      const context = template.contexts[Math.floor(Math.random() * template.contexts.length)];
      const emotion = emotionLevels[Math.floor(Math.random() * emotionLevels.length)];
      
      // 生成随机时间戳（过去30天内）
      const now = new Date();
      const daysAgo = Math.floor(Math.random() * 30);
      const hoursAgo = Math.floor(Math.random() * 24);
      const minutesAgo = Math.floor(Math.random() * 60);
      const recordDate = new Date(now);
      recordDate.setDate(now.getDate() - daysAgo);
      recordDate.setHours(now.getHours() - hoursAgo);
      recordDate.setMinutes(now.getMinutes() - minutesAgo);
      
      const behaviorRecord = {
        id: generateId(),
        child_id: childId,
        timestamp: recordDate.toISOString(),
        behavior_type: template.type,
        description: `${template.antecedent} → ${template.behavior} → ${template.consequence}`,
        emotion_level: emotion.level,
        context: context,
        notes: `情绪状态: ${emotion.desc}`,
        abc_antecedent: template.antecedent,
        abc_behavior: template.behavior,
        abc_consequence: template.consequence
      };
      
      const result = await postRequest('/api/records', behaviorRecord);
      if (result.success) {
        totalRecords++;
      } else {
        console.log(`    ✗ 记录 ${i+1} 失败:`, result.error);
      }
      
      // 稍微延迟，避免请求过快
      await new Promise(resolve => setTimeout(resolve, 50));
    }
  }
  
  console.log('\n数据生成完成！');
  console.log(`总计: ${childIds.length} 名儿童, ${parentIds.length} 位家长, ${professionalIds.length} 个机构, ${totalRecords} 条行为记录`);
  
  // 5. 生成一份家长评估问卷响应
  console.log('\n生成家长评估问卷数据...');
  if (parentIds.length > 0) {
    const parentAssessment = {
      id: generateId(),
      parent_id: parentIds[0],
      child_id: childIds[0],
      assessment_date: new Date().toISOString().split('T')[0],
      relationship_quality: 4,
      communication_effectiveness: 3,
      skill_mastery_level: 2,
      daily_available_hours: 3.5,
      weekly_available_days: 5,
      stress_level: 4,
      support_needs: JSON.stringify(['行为管理技巧', '情绪调节策略', '家校合作']),
      strengths: '有耐心，学习意愿强',
      challenges: '缺乏专业知识和实践机会',
      goals: '希望提高孩子的社交技能和语言能力'
    };
    
    const result = await postRequest('/api/parent-assessments', parentAssessment);
    if (result.success) {
      console.log(`  ✓ 创建家长评估问卷`);
    } else {
      console.log(`  ✗ 创建家长评估问卷失败:`, result.error);
    }
  }
  
  console.log('\n所有模拟数据生成完毕！');
  console.log('\n服务器地址: http://localhost:3000');
  console.log('可以使用以下命令查看数据:');
  console.log('  curl http://localhost:3000/api/children');
  console.log('  curl http://localhost:3000/api/records?limit=10');
}

// 运行生成器
generateMockData().catch(err => {
  console.error('生成数据时出错:', err);
  process.exit(1);
});