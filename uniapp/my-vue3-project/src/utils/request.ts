
// 修改HTTP请求处理中的Content-Type问题
const request = async (url: string, options: UniApp.RequestOptions) => {
  
  // 确保设置正确的Content-Type
  if (!options.header) {
    options.header = {}
  }
  // 如果没有指定Content-Type，则默认为application/json
  if (!options.header['Content-Type'] && !options.header['content-type']) {
    options.header['Content-Type'] = 'application/json'
  }
  
}