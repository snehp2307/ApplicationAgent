# 🤝 Contributing to Bulk AI Job Outreach Bot

Thank you for your interest in contributing! This guide will help you get started.

---

## 📋 How to Contribute

### 1. Fork the Repository

Click the **Fork** button on the GitHub repository page.

### 2. Clone Your Fork

```bash
git clone https://github.com/YOUR_USERNAME/bulk-ai-job-outreach.git
cd bulk-ai-job-outreach
```

### 3. Create a Branch

```bash
git checkout -b feature/your-feature-name
```

### 4. Make Your Changes

- Follow the existing code style and structure
- Add docstrings to new functions
- Test your changes locally before submitting

### 5. Commit and Push

```bash
git add .
git commit -m "feat: description of your change"
git push origin feature/your-feature-name
```

### 6. Open a Pull Request

Go to the original repository and click **New Pull Request**.

---

## 📐 Code Style

- **Python 3.11+** compatible
- Use **type hints** where possible
- Include **docstrings** for all functions
- Follow **PEP 8** conventions
- Keep functions focused and modular

---

## 🔒 Security Rules

- **NEVER** commit `.env` files or API keys
- **NEVER** commit resume PDF files
- **NEVER** commit output CSV/log files with real data
- Always use `.env.example` for configuration templates

---

## 💡 Ideas for Contributions

- Add support for additional LLM providers (OpenAI, Anthropic)
- Improve email template variety
- Add unit tests
- Improve company name extraction accuracy
- Add support for additional email providers (Outlook, Yahoo)
- Create a web-based monitoring dashboard
- Add email scheduling capabilities

---

## 🐛 Reporting Bugs

Open an [Issue](../../issues) with:

1. A clear title describing the bug
2. Steps to reproduce
3. Expected vs. actual behavior
4. Your Python version and OS
5. Any relevant error messages (redact API keys!)

---

## 📄 License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
