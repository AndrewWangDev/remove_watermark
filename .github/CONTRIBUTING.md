# Contributing to remove_watermark

Thank you for your interest in contributing to `remove_watermark`! We welcome contributions, bug reports, and suggestions from the community.

Please take a moment to review this document before submitting your contribution.

---

## Code of Conduct

This project is governed by the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

---

## How Can I Contribute?

### 1. Reporting Bugs
- Before creating an issue, please search existing [Issues](https://github.com/AndrewWangDev/remove_watermark/issues) to ensure it hasn't been reported or addressed already.
- If reporting a new bug, use the **Bug Report** template and provide:
  - Clear steps to reproduce the problem.
  - Expected behavior vs. actual behavior.
  - OS version and Python environment (`python --version`).
  - Terminal logs or traceback if applicable.

> [!NOTE]
> For security vulnerabilities, please refer to our [Security Policy](SECURITY.md) instead of creating a public issue.

### 2. Suggesting Enhancements
- Open a feature request via [Issues](https://github.com/AndrewWangDev/remove_watermark/issues/new/choose) using the **Feature Request** template.
- Explain why the enhancement would be valuable and provide details on the desired behavior or algorithm.

### 3. Code Contributions (Pull Requests)

#### Local Development Setup
1. Fork and clone the repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/remove_watermark.git
   cd remove_watermark
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On Linux/macOS:
   source venv/bin/activate

   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. Run the application from source:
   ```bash
   python src/main.py
   ```

#### Running Tests
Always run the automated test suite locally before pushing changes or opening a PR:
```bash
python tests/test_watermark.py
```
Ensure all tests pass cleanly.

#### Coding Standards
- Follow standard Python **PEP 8** style guidelines.
- Keep algorithms vectorized using NumPy and OpenCV whenever possible—avoid pure Python nested loops over pixels.
- Ensure cross-platform compatibility (paths must work across Windows, Linux, and macOS).
- Maintain documentation integrity: preserve docstrings and explain mathematical reasoning for signal processing filters.

#### Commit Message Guidelines
We follow standard Conventional Commits:
- `feat(algorithms): add ...`
- `fix(ui): resolve ...`
- `ci: update ...`
- `test: add unit test for ...`
- `docs: update ...`

#### Submitting a Pull Request
1. Branch from `main`:
   ```bash
   git checkout -b feat/my-new-feature
   ```
2. Commit your changes with descriptive messages.
3. Push to your fork:
   ```bash
   git push origin feat/my-new-feature
   ```
4. Open a Pull Request against `main`. Fill in the PR template details and ensure all CI checks pass.
