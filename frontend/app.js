// app.js
App({
  onLaunch() {
    console.log('行为观察伙伴小程序启动')
  },
  globalData: {
    userInfo: null,
    baseUrl: 'https://47.103.229.125'  // 后端 API 地址
  }
})
