# 快速开始指南

## 🏃 5 分钟快速开始

### 本地运行
```bash
cd reading
python server.py
```
打开浏览器访问 **http://localhost:3000**

### 和朋友分享（三选一）

#### ✅ 方案 A：云部署（最简单，推荐）

**只需 5 分钟，一键部署到公网！**

**步骤 1**：创建 GitHub 仓库
- 访问 https://github.com/new
- 创建仓库 `reading-club`

**步骤 2**：上传代码
```bash
git init
git add .
git commit -m "Initial"
git remote add origin https://github.com/你的用户名/reading-club.git
git push -u origin main
```

或者直接运行：
- Windows: 双击 `deploy.bat`
- Mac/Linux: `bash deploy.sh`

**步骤 3**：部署到 Render（免费）
1. 访问 https://render.com
2. 用 GitHub 账号登录
3. 点击 **New +** → **Web Service**
4. 选择 `reading-club` 仓库
5. 选择 **Free** 计划
6. 点击 **Deploy**

**等待 2-3 分钟后**，你会得到一个公网链接，比如：
```
https://reading-club-xyz.onrender.com
```

**分享这个链接给所有朋友，他们就能访问了！**

---

#### 📱 方案 B：本地网络分享（没有外网时）

如果只是在家里或办公室局域网内使用：

1. 本机运行 `python server.py`
2. 查看本机 IP（Windows: `ipconfig` | Mac/Linux: `ifconfig`）
3. 分享 `http://你的IP:3000` 给朋友

朋友在同一个网络下就能访问了。

---

#### 💾 方案 C：手动同步（最简单但需要定期处理）

1. 在本地运行应用
2. 定期把 `data/books.json` 保存到共享文件夹（Google Drive/Dropbox）
3. 启动应用前从共享文件夹拉取最新的 JSON

**缺点**：需要手动同步，不能实时编辑

---

## 📖 使用提示

### 添加书籍
1. 输入书名和作者，点击 **🔍 搜索**
2. Open Library 会自动显示匹配的书籍
3. 点击选择，自动填充：详情、评分、封面、分类
4. 点击 **添加**

### 投票与管理
- **❤️ 想读**：投票你最想读的书
- **📋 → 📖 → ✅**：改变状态（备选 → 在读 → 已读）
- **🗑️ 删除**：移除不想看的书

### 书评与讨论
- 读完后点 **💬 书评**
- 撰写书评并打星
- 朋友可以在下面评论讨论
- **所有操作都会显示你的昵称**

---

## ⚙️ 常见问题

**Q: 要花钱吗？**
A: 完全免费。Render 和 Railway 都提供免费额度。

**Q: 朋友看不到我的更新？**
A: 页面每 5 秒自动同步一次，稍等一会就能看到。

**Q: 数据会丢失吗？**
A: 不会。数据永久保存在 `books.json`。

**Q: 想自定义分类/颜色？**
A: 编辑 `public/index.html` 即可。

**Q: 想添加注册登录功能？**
A: 编辑 `server.py` 添加数据库支持即可。

---

## 🎯 推荐流程

1. **本地测试** → 运行 `python server.py` 测试功能
2. **上传 GitHub** → `git push` 到你的仓库
3. **部署上网** → 在 Render 上一键部署
4. **分享链接** → 告诉朋友公网地址
5. **开始阅读** → 一起选书、读书、评书！

---

**有问题？代码很简洁，直接改源码吧！😊**
