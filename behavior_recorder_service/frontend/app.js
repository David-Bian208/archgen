// app.js
App({
  onLaunch() {
    console.log('行为观察伙伴小程序启动')
  },
  globalData: {
    userInfo: null,
    baseUrl: 'http://localhost:8000'  // 本地开发用 localhost
    // 发布时改为公网地址：'https://your-domain.com'
  }
})
