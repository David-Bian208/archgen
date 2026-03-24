// app.js
App({
  onLaunch() {
    console.log('行为观察伙伴小程序启动')
  },
  globalData: {
    userInfo: null,
    baseUrl: 'http://47.103.229.125:8000'  // 服务器公网 IP
  }
})
