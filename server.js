const express = require('express');
const fs = require('fs');
const path = require('path');
const { v4: uuidv4 } = require('uuid');

const app = express();
const PORT = 3000;
const DATA_FILE = path.join(__dirname, 'data', 'books.json');

app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// ========== 数据读写 ==========

function readData() {
  if (!fs.existsSync(DATA_FILE)) {
    const initial = { books: [] };
    fs.mkdirSync(path.dirname(DATA_FILE), { recursive: true });
    fs.writeFileSync(DATA_FILE, JSON.stringify(initial, null, 2), 'utf-8');
    return initial;
  }
  return JSON.parse(fs.readFileSync(DATA_FILE, 'utf-8'));
}

function writeData(data) {
  fs.mkdirSync(path.dirname(DATA_FILE), { recursive: true });
  fs.writeFileSync(DATA_FILE, JSON.stringify(data, null, 2), 'utf-8');
}

// ========== 书籍 API ==========

// 获取所有书籍
app.get('/api/books', (req, res) => {
  const data = readData();
  res.json(data.books);
});

// 添加书籍
app.post('/api/books', (req, res) => {
  const data = readData();
  const book = {
    id: uuidv4(),
    title: req.body.title || '',
    author: req.body.author || '',
    synopsis: req.body.synopsis || '',
    rating: req.body.rating || null,
    ratingSource: req.body.ratingSource || '',
    category: req.body.category || '未分类',
    cover: req.body.cover || '',
    addedBy: req.body.addedBy || '匿名',
    addedAt: new Date().toISOString(),
    status: 'candidate',  // candidate / reading / finished
    votes: {},
    reviews: []
  };
  data.books.push(book);
  writeData(data);
  res.json(book);
});

// 删除书籍
app.delete('/api/books/:id', (req, res) => {
  const data = readData();
  const idx = data.books.findIndex(b => b.id === req.params.id);
  if (idx === -1) return res.status(404).json({ error: '书籍未找到' });
  const removed = data.books.splice(idx, 1);
  writeData(data);
  res.json(removed[0]);
});

// 更新书籍信息
app.put('/api/books/:id', (req, res) => {
  const data = readData();
  const book = data.books.find(b => b.id === req.params.id);
  if (!book) return res.status(404).json({ error: '书籍未找到' });
  const allowed = ['title', 'author', 'synopsis', 'rating', 'ratingSource', 'category', 'cover', 'status'];
  allowed.forEach(key => {
    if (req.body[key] !== undefined) book[key] = req.body[key];
  });
  writeData(data);
  res.json(book);
});

// 投票想读
app.post('/api/books/:id/vote', (req, res) => {
  const data = readData();
  const book = data.books.find(b => b.id === req.params.id);
  if (!book) return res.status(404).json({ error: '书籍未找到' });
  const userId = req.body.userId || '匿名';
  if (book.votes[userId]) {
    delete book.votes[userId];
  } else {
    book.votes[userId] = true;
  }
  writeData(data);
  res.json(book);
});

// ========== 书评 API ==========

// 添加书评
app.post('/api/books/:id/reviews', (req, res) => {
  const data = readData();
  const book = data.books.find(b => b.id === req.params.id);
  if (!book) return res.status(404).json({ error: '书籍未找到' });
  const review = {
    id: uuidv4(),
    userId: req.body.userId || '匿名',
    content: req.body.content || '',
    rating: req.body.rating || null,
    createdAt: new Date().toISOString(),
    comments: []
  };
  book.reviews.push(review);
  writeData(data);
  res.json(review);
});

// 删除书评
app.delete('/api/books/:bookId/reviews/:reviewId', (req, res) => {
  const data = readData();
  const book = data.books.find(b => b.id === req.params.bookId);
  if (!book) return res.status(404).json({ error: '书籍未找到' });
  const idx = book.reviews.findIndex(r => r.id === req.params.reviewId);
  if (idx === -1) return res.status(404).json({ error: '书评未找到' });
  book.reviews.splice(idx, 1);
  writeData(data);
  res.json({ success: true });
});

// ========== 评论/讨论 API ==========

// 添加评论到书评
app.post('/api/books/:bookId/reviews/:reviewId/comments', (req, res) => {
  const data = readData();
  const book = data.books.find(b => b.id === req.params.bookId);
  if (!book) return res.status(404).json({ error: '书籍未找到' });
  const review = book.reviews.find(r => r.id === req.params.reviewId);
  if (!review) return res.status(404).json({ error: '书评未找到' });
  const comment = {
    id: uuidv4(),
    userId: req.body.userId || '匿名',
    content: req.body.content || '',
    createdAt: new Date().toISOString()
  };
  review.comments.push(comment);
  writeData(data);
  res.json(comment);
});

// 删除评论
app.delete('/api/books/:bookId/reviews/:reviewId/comments/:commentId', (req, res) => {
  const data = readData();
  const book = data.books.find(b => b.id === req.params.bookId);
  if (!book) return res.status(404).json({ error: '书籍未找到' });
  const review = book.reviews.find(r => r.id === req.params.reviewId);
  if (!review) return res.status(404).json({ error: '书评未找到' });
  const idx = review.comments.findIndex(c => c.id === req.params.commentId);
  if (idx === -1) return res.status(404).json({ error: '评论未找到' });
  review.comments.splice(idx, 1);
  writeData(data);
  res.json({ success: true });
});

// ========== 启动 ==========

app.listen(PORT, () => {
  console.log(`📚 阅读计划管理工具已启动: http://localhost:${PORT}`);
});
