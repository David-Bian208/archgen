"""ABC 引导话术模板 - V6.3"""

# 首轮教育话术（当用户首次输入信息不完整时）
ABC_EDUCATION_INTRO = """理解您的困扰。为了更准确地分析，我们用**ABC 行为分析框架**来收集信息——把行为拆成三个环节：

**A 前因**：行为发生前，孩子在哪里？和谁？在做什么？
**B 行为**：孩子具体做了什么？（越具体越好，如"大声哭了约3分钟"）
**C 后果**：您或周围人怎么反应的？最后怎么样了？

想到什么说什么，不用全部回答。

您可以一次性说完 A-B-C，也可以我们一步步来。

💡 **回忆提示**：孩子当时的状态如何（饿了/困了/累了）？是第一次还是经常发生？"""

# 分步引导话术
GUIDE_ANTECEDENT = "我们先从 A 前因开始回忆——{question}"
GUIDE_BEHAVIOR = "现在我们回忆行为（B）——{question}"
GUIDE_CONSEQUENCE = "最后想一下后果（C）——{question}"

# 引导问题
QUESTION_ANTECEDENT = "{event}发生前，孩子在哪里？正在做什么？有没有什么特别的事？"
QUESTION_BEHAVIOR = "他/她具体做了什么？是大声哭喊、躺在地上、还是其他动作？持续了多久？"
QUESTION_CONSEQUENCE = "您当时是怎么处理的？最后怎么样了？"

# 确认话术
CONFIRM_ANTECEDENT = "好的，前因清楚了——{value}。"
CONFIRM_BEHAVIOR = "明白了，行为也清楚了——{value}。"
CONFIRM_CONSEQUENCE = """收到，信息已经收集完整了——
前因：{antecedent}
行为：{behavior}
后果：{consequence}
我现在开始为您分析，请稍等..."""

# 过渡声明
TRANSITION_COMPLETE = "收到，信息已经收集完整了。我现在开始为您分析，请稍等..."
TRANSITION_PARTIAL = "我们已经收集了一些信息，我先基于现有内容为您生成初步分析。后续如果您能补充更多细节，分析会更加精准。"

# 注意：V6.3 不提供跳过功能
# 已经引导了，连 ABC 都不完成，这个工具以后也不会使用
