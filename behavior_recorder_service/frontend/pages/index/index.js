// pages/index/index.js
const app = getApp()

Page({
  data: {
    userInput: '',
    isAnalyzing: false,
    report: null,
    rating: 0,
    accuracy: '',
    feedbackText: '',
    sessionId: ''
  },

  onLoad() {
    // 生成会话 ID
    this.setData({
      sessionId: 'session_' + Date.now()
    })
  },

  // 输入框内容变化
  onInput(e) {
    this.setData({
      userInput: e.detail.value
    })
  },

  // 发送分析请求
  async sendRequest() {
    const { userInput, sessionId } = this.data
    
    if (!userInput.trim()) {
      wx.showToast({
        title: '请输入行为描述',
        icon: 'none'
      })
      return
    }

    this.setData({ isAnalyzing: true })

    try {
      const response = await wx.request({
        url: `${app.globalData.baseUrl}/api/v4/chat`,
        method: 'POST',
        data: {
          user_input: userInput,
          session_id: sessionId
        },
        timeout: 60000  // 60 秒超时
      })

      if (response.data.status === 'success') {
        this.setData({
          report: response.data.data,
          isAnalyzing: false
        })

        wx.showToast({
          title: '分析完成',
          icon: 'success'
        })
      } else {
        throw new Error(response.data.message || '分析失败')
      }
    } catch (error) {
      console.error('分析失败:', error)
      this.setData({ isAnalyzing: false })
      
      wx.showModal({
        title: '分析失败',
        content: error.message || '请稍后重试',
        showCancel: false
      })
    }
  },

  // 设置评分
  setRating(e) {
    const rating = parseInt(e.currentTarget.dataset.rating)
    this.setData({ rating })
  },

  // 设置准确性
  setAccuracy(e) {
    const accuracy = e.currentTarget.dataset.accuracy
    this.setData({ accuracy })
  },

  // 反馈输入
  onFeedbackInput(e) {
    this.setData({
      feedbackText: e.detail.value
    })
  },

  // 提交反馈
  async submitFeedback() {
    const { sessionId, rating, accuracy, feedbackText } = this.data

    if (rating === 0) {
      wx.showToast({
        title: '请先评分',
        icon: 'none'
      })
      return
    }

    try {
      await wx.request({
        url: `${app.globalData.baseUrl}/api/v4/feedback`,
        method: 'POST',
        data: {
          session_id: sessionId,
          rating,
          accuracy,
          feedback_text: feedbackText
        }
      })

      wx.showToast({
        title: '反馈已提交',
        icon: 'success'
      })

      // 清空反馈
      this.setData({
        rating: 0,
        accuracy: '',
        feedbackText: ''
      })
    } catch (error) {
      console.error('提交反馈失败:', error)
      wx.showToast({
        title: '提交失败',
        icon: 'none'
      })
    }
  },

  // 开始新记录
  startNew() {
    this.setData({
      userInput: '',
      report: null,
      rating: 0,
      accuracy: '',
      feedbackText: '',
      sessionId: 'session_' + Date.now()
    })
  }
})
