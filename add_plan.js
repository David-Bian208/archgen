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

async function addPlanAndTasks() {
  console.log('开始添加干预计划和今日任务...\n');
  
  // 小明的ID
  const childId = 'mm76eyu8p9wtzxuw3c';
  const today = new Date().toISOString().split('T')[0];
  
  // 1. 创建干预计划
  const planId = generateId();
  const plan = {
    id: planId,
    child_id: childId,
    title: '小明社交沟通能力提升计划',
    description: '针对小明的社交沟通障碍，制定为期一个月的综合干预计划，重点提升眼神交流、简单对话和情绪识别能力。',
    start_date: today,
    end_date: new Date(new Date().setDate(new Date().getDate() + 30)).toISOString().split('T')[0],
    status: '进行中',
    target_skills: '社交互动、沟通表达、情绪识别',
    baseline_assessment: '眼神接触少于2秒，无主动社交发起，理解简单指令困难',
    target_outcomes: '能够维持3-5秒眼神接触，主动发起简单社交互动，理解并执行2步指令',
    created_by: '系统管理员'
  };
  
  console.log('创建干预计划...');
  const planResult = await postRequest('/api/plans', plan);
  
  if (!planResult.success) {
    console.log('❌ 创建计划失败:', planResult.error);
    return;
  }
  
  console.log('✅ 计划创建成功:', plan.title);
  
  // 2. 创建今日任务
  const tasks = [
    {
      id: generateId(),
      plan_id: planId,
      title: '眼神交流游戏',
      description: '与小明玩"躲猫猫"游戏，每次露脸时尝试与他进行眼神接触，目标累计3次成功对视（每次至少2秒）',
      domain: '社交互动',
      priority: '高',
      difficulty: '简单',
      frequency: '每天',
      assigned_date: today, // 今天
      task_type: '游戏活动',
      duration_minutes: 15,
      assigned_to: '家长',
      materials_needed: '手帕或小毯子',
      success_criteria: '完成3次成功对视，每次至少2秒',
      baseline_level: '当前：少于2秒',
      target_level: '目标：3-5秒',
      completed: 0
    },
    {
      id: generateId(),
      plan_id: planId,
      title: '情绪卡片识别',
      description: '使用情绪卡片（开心、难过、生气），帮助小明识别基本情绪，尝试让他模仿相应表情',
      domain: '情绪识别',
      priority: '中',
      difficulty: '中等',
      frequency: '每天',
      assigned_date: today,
      task_type: '学习活动',
      duration_minutes: 10,
      assigned_to: '家长',
      materials_needed: '情绪卡片或图片',
      success_criteria: '能够正确识别2种基本情绪（开心/难过）',
      baseline_level: '当前：无法识别情绪',
      target_level: '目标：识别2种情绪',
      completed: 0
    },
    {
      id: generateId(),
      plan_id: planId,
      title: '简单指令练习',
      description: '练习两步指令："拿起球，给我"或"打开门，坐下"，使用视觉提示和示范',
      domain: '沟通表达',
      priority: '中',
      difficulty: '中等',
      frequency: '每天',
      assigned_date: today,
      task_type: '训练活动',
      duration_minutes: 20,
      assigned_to: '家长',
      materials_needed: '球、椅子等实物',
      success_criteria: '能够正确执行1-2个两步指令',
      baseline_level: '当前：只能执行单步指令',
      target_level: '目标：执行两步指令',
      completed: 0
    },
    {
      id: generateId(),
      plan_id: planId,
      title: '社交故事阅读',
      description: '阅读关于"和朋友分享玩具"的社交故事，讨论故事中的情境和适当行为',
      domain: '社交互动',
      priority: '低',
      difficulty: '简单',
      frequency: '每周',
      assigned_date: today,
      task_type: '阅读活动',
      duration_minutes: 10,
      assigned_to: '家长',
      materials_needed: '社交故事书或打印材料',
      success_criteria: '安静听完故事，能够回答1个简单问题',
      baseline_level: '当前：注意力短暂',
      target_level: '目标：专注10分钟',
      completed: 0
    }
  ];
  
  console.log('\n创建今日任务...');
  let successCount = 0;
  
  for (const task of tasks) {
    const taskResult = await postRequest('/api/tasks', task);
    if (taskResult.success) {
      successCount++;
      console.log(`  ✅ ${task.title}`);
    } else {
      console.log(`  ❌ ${task.title}: ${taskResult.error}`);
    }
    
    // 稍微延迟
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  
  console.log(`\n✅ 计划创建完成！`);
  console.log(`- 计划: ${plan.title}`);
  console.log(`- 计划ID: ${planId}`);
  console.log(`- 关联儿童: 小明`);
  console.log(`- 今日任务: ${successCount}/${tasks.length} 个`);
  console.log(`- 计划周期: ${plan.start_date} 至 ${plan.end_date}`);
  console.log(`\n现在首页的"今日计划"将显示这些任务。`);
}

// 执行
addPlanAndTasks().catch(err => {
  console.error('脚本执行错误:', err);
});