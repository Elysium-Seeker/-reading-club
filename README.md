# 📚 阅读计划 - 多人协作工具

一个简单易用的网页应用，让你和朋友们轻松管理共同的阅读计划。

## ✨ 功能特性

- **📖 书籍管理** - 添加书籍时支持一键搜索自动填充信息
- **⭐ 评分与简介** - 自动从 Open Library 获取评分、简介、分类
- **🤍 投票想读** - 朋友投票决定先读谁喜欢的书
- **💬 书评讨论** - 读完后可发布书评、评分、相互讨论
- **👤 身份标识** - 所有操作（投票、书评、评论）都带上自己的昵称
- **📱 实时同步** - 多人同时访问，5秒自动同步数据
- **🔍 强大检索** - 按书名、作者、分类搜索，多维度排序

## 🚀 快速开始（本地运行）

### 需求
- Python 3.6+ （无需安装任何Python包）

### 运行
```bash
cd reading
python server.py
```

然后在浏览器打开 **http://localhost:3000**

> **提示**：在右上角输入你的昵称，这样其他人就知道是你在操作了！

## ☁️ 部署到云平台（免费）

### 方案 1：Render（推荐）

**优点**: 免费，无需信用卡，Python 原生支持

1. **上传代码到 GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/你的用户名/reading-club.git
   git push -u origin main
   ```

2. **连接 Render**
   - 访问 [render.com](https://render.com)
   - 用 GitHub 账号登录
   - 点击 **New +** > **Web Service**
   - 选择上面的仓库
   - 填写配置：
     - **Name**: `reading-club`
     - **Runtime**: `Python 3`
     - **Build**: `pip install -r requirements.txt`
     - **Start**: `python server.py`
   - 点击 **Deploy**

3. **等待部署完成**
   - 大约需要 2-3 分钟
   - 完成后会得到一个公网 URL，类似 `https://reading-club-xyz.onrender.com`
   - 分享这个链接给所有朋友！

### 方案 2：Railway

1. **连接 Railway**
   - 访问 [railway.app](https://railway.app)
   - 用 GitHub 登录并授权
   - 点击 **New Project** > **Deploy from GitHub repo**
   - 选择 `reading-club` 仓库

2. **配置镜像变量**
   - 添加变量 `PORT` = `3000`
   - 其他保持默认

3. **部署完毕**
   - Railway 会自动检测 Python 并部署
   - 在 **Deployments** 中找到公网 URL

### 方案 3：Heroku（免费额度可能有限）

1. **安装 Heroku CLI**
   ```bash
   # 访问 https://devcenter.heroku.com/articles/heroku-cli
   ```

2. **部署**
   ```bash
   heroku login
   heroku create reading-club-你的名字
   git push heroku main
   ```

3. **获取 URL**
   ```bash
   heroku open
   ```

## 🔧 本地开发

### 添加你自己的书
```
1. 输入书名和作者
2. 点击 🔍 搜索
3. 从结果中选择（自动填充信息）
4. 或手工输入，点击"添加"
```

### 投票与状态
- ❤️ **想读** - 投票你想读的书
- **📋 备选** - 备选书单
- **📖 在读** - 正在读
- **✅ 已读** - 读过了

### 书评与讨论
- 推荐读完后立即撰写书评
- 每条评论都会显示你的昵称和时间
- 朋友可以直接在书评下回复讨论

## 📝 配置说明

### 数据存储
- 数据保存在 `data/books.json`
- 每次操作自动保存
- 可直接编辑 JSON 文件

### 自定义端口
```bash
# Linux/Mac
PORT=8080 python server.py

# Windows (PowerShell)
$env:PORT=8080; python server.py
```

### 添加更多分类
编辑 `public/index.html` 中的 `<select id="inputCategory">` 部分

## 🎨 外观定制

所有样式在 `public/index.html` 的 `<style>` 标签中，可随意修改：
- 颜色主题变量在 `:root` 块
- 布局 CSS 在后续部分

## 📖 API 文档

### 获取所有书籍
```
GET /api/books
返回: [{id, title, author, reviews, votes, ...}]
```

### 搜索书籍
```
GET /api/search-book?title=书名&author=作者
返回: [{title, author, rating, synopsis, ...}]
```

### 添加书籍
```
POST /api/books
Body: {title, author, synopsis, rating, category, cover, addedBy}
```

### 投票
```
POST /api/books/{bookId}/vote
Body: {userId}
```

### 发布书评
```
POST /api/books/{bookId}/reviews
Body: {userId, content, rating}
```

### 回复书评
```
POST /api/books/{bookId}/reviews/{reviewId}/comments
Body: {userId, content}
```

## ❓ 常见问题

**Q: 为什么搜索不到某本书？**
A: 系统使用 Open Library 数据库，数据库中没有的书无法搜索。可手动输入信息。

**Q: 数据会丢失吗？**
A: 不会。数据保存在 `books.json` 文件中。即使云平台重启也不会丢失。

**Q: 可以自建数据库吗？**
A: 可以。修改 `server.py` 中的 `read_data()` 和 `write_data()` 函数，连接你的数据库。

**Q: 支持用户注册和登录吗？**
A: 当前版本不需要——只需在右上角输入昵称即可。如需身份验证，可自行修改。

**Q: 可以导出数据吗？**
A: 在云平台面板中下载 `books.json` 即可导出所有数据。

## 📄 许可证

自由使用，无任何限制。

## 🤝 如何贡献

直接修改代码并 push 即可 :)

---

**开心阅读！📚**

有问题？直接修改代码吧，代码很简洁容易改的！
