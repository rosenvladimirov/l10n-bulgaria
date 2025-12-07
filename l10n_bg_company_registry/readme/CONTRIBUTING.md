# Contributing to Bulgarian Company Registry Integration

Thank you for your interest in contributing to this project! 🎉

## How to Contribute

### Reporting Bugs

If you find a bug, please create an issue with:

1. **Clear description** of the problem
2. **Steps to reproduce** the issue
3. **Expected behavior** vs. actual behavior
4. **Odoo version** you're using
5. **Sample EIK** that demonstrates the issue (if applicable)
6. **HAR file** of the API response (optional but very helpful!)

### Suggesting Enhancements

We welcome feature requests! Please include:

1. **Use case** - Why is this feature needed?
2. **Proposed solution** - How should it work?
3. **Alternatives considered** - What other options did you think about?

### Code Contributions

#### Before You Start

1. Check existing issues and pull requests
2. Discuss major changes in an issue first
3. Make sure you understand the [Odoo coding guidelines](https://www.odoo.com/documentation/16.0/contributing/development/coding_guidelines.html)

#### Development Setup

```bash
# Clone the repository
git clone <repository-url>

# Create a new branch
git checkout -b feature/your-feature-name

# Install development dependencies
pip install -r requirements-dev.txt  # If available
```

#### Code Style

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) for Python code
- Use 4 spaces for indentation (no tabs)
- Maximum line length: 100 characters (flexibility for readability)
- Use meaningful variable and function names
- Add docstrings to all functions and methods

**Example:**

```python
def _parse_bulgarian_address(self, address_text):
    """
    Parse Bulgarian address into structured components.
    
    Args:
        address_text (str): Full address text from registry
        
    Returns:
        dict: Structured address with keys like 'city', 'street', 'zip'
        
    Example:
        >>> address = "гр. София 1000, ул. Витоша № 1"
        >>> result = self._parse_bulgarian_address(address)
        >>> print(result['city'])
        'София'
    """
    # Implementation here
    pass
```

#### XML Style

- Indent with 4 spaces
- Use meaningful record IDs
- Follow Odoo view structure guidelines
- Add comments for complex views

#### Commit Messages

Use clear, descriptive commit messages:

```
[FIX] module_name: Brief description of the fix

Detailed explanation if needed.

Fixes #issue_number
```

**Prefixes:**
- `[FIX]` - Bug fixes
- `[ADD]` - New features
- `[IMP]` - Improvements to existing features
- `[REF]` - Code refactoring
- `[REM]` - Removed features
- `[MOV]` - Moved files
- `[MERGE]` - Merge commits

#### Testing Requirements

**Critical: Address Parsing Changes**

If you modify address parsing, you **MUST** test with at least these scenarios:

- [ ] Company with `ул.` (street) address
- [ ] Company with `бул.` (boulevard) address
- [ ] Company with `ж.к.` (residential complex) address
- [ ] Multi-word street names (e.g., names with 2+ words)
- [ ] Address with email contact
- [ ] Address with phone contact
- [ ] Address from Sofia
- [ ] Address from another major city (Varna, Plovdiv, Burgas)
- [ ] Address with building/entrance/floor/apartment details
- [ ] Street name with special characters or quotes

**Test Script Template:**

```python
# Test your changes with real EIKs
test_eiks = [
    'XXXXXXXXX',  # ул. address
    'XXXXXXXXX',  # бул. address
    'XXXXXXXXX',  # ж.к. address
    'XXXXXXXXX',  # street with quotes
]

for eik in test_eiks:
    wizard = env['bg.company.search.wizard'].create({'eik': eik})
    wizard.action_search_registry()
    # Verify all fields populated correctly
```

**Success Criteria:**
- 100% field population for all test cases
- No errors in logs
- Address components correctly extracted

#### Pull Request Process

1. **Update documentation** if you've changed behavior
2. **Add/update tests** if applicable
3. **Update CHANGELOG.md** with your changes
4. **Ensure all tests pass**
5. **Create pull request** with clear description

**Pull Request Template:**

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Improvement
- [ ] Documentation update

## Testing Done
- [ ] Tested with X companies
- [ ] All address types work
- [ ] No errors in logs
- [ ] Updated documentation

## Checklist
- [ ] My code follows the project's style guidelines
- [ ] I have added docstrings to new functions
- [ ] I have updated the documentation
- [ ] I have added tests for my changes
- [ ] All tests pass
- [ ] I have updated CHANGELOG.md

## Related Issues
Fixes #issue_number
```

### Documentation Contributions

Documentation improvements are always welcome!

- Fix typos
- Improve explanations
- Add examples
- Translate to other languages
- Update screenshots

### Testing Contributions

Help us improve by:

- Testing with different Odoo versions
- Testing with edge cases
- Providing HAR files from problematic companies
- Creating automated test suites

## Development Guidelines

### Address Parsing Development

When working on address parsing:

1. **Never break existing functionality** - Always test with previous test cases
2. **Add new edge cases** - Document any new formats you discover
3. **Preserve structure** - Maintain line breaks and formatting
4. **Extract intelligently** - Don't just split on commas
5. **Handle Unicode properly** - Bulgarian text has specific characters

### API Integration

When working with the registry API:

1. **Handle timeouts gracefully** - Default 30 seconds
2. **Validate responses** - Check for errors before parsing
3. **Log appropriately** - Use proper log levels (DEBUG, INFO, WARNING, ERROR)
4. **Don't hammer the API** - Be respectful of the public service

### Database Changes

**Important:** This module should work WITHOUT database changes!

- Don't add new models unless absolutely necessary
- Don't modify `res.partner` structure directly
- Use transient models for wizards
- Respect existing field naming conventions

## Questions?

Feel free to ask questions by:

1. Creating an issue with the "question" label
2. Contacting the author directly
3. Checking existing documentation

## Code of Conduct

### Our Pledge

We pledge to make participation in our project a harassment-free experience for everyone.

### Our Standards

**Positive behavior includes:**
- Using welcoming and inclusive language
- Being respectful of differing viewpoints
- Accepting constructive criticism gracefully
- Focusing on what is best for the community

**Unacceptable behavior includes:**
- Harassment of any kind
- Trolling or insulting comments
- Publishing others' private information
- Other conduct which could reasonably be considered inappropriate

### Enforcement

Instances of abusive behavior may be reported by contacting the project author.

## Attribution

Thank you to all contributors who help make this project better!

---

**Happy Coding!** 🚀

Remember: Good code is not just code that works, it's code that others can understand and maintain.
