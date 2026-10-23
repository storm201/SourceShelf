# Security Policy

## Reporting Security Issues

We take the security of SourceShelf seriously. If you discover a security vulnerability, please report it responsibly.

### How to Report
- **Preferred Method**: Open a confidential security advisory on GitHub via the **Security** tab -> **Advisories** -> **New draft security advisory**.
- **Alternative**: If private advisories are unavailable, contact the repository maintainer directly before publishing public details or opening a public issue.

Please include:
- A description of the issue and potential impact
- Steps or a minimal proof of concept to reproduce the behavior
- Affected components (frontend, crawler, GitHub Actions workflow, database schema)

### Scope
- The public static web application
- The automated GitHub Actions crawler and build scripts
- Supabase schema and RLS policies

### Out of Scope
- Third-party repositories indexed by SourceShelf (report those to their respective maintainers)
- Denial-of-service against third-party APIs (e.g. GitHub API rate limits)
- Attacks requiring physical access to a user's machine or browser devtools tampering

### Response Timeline
- We will acknowledge receipt of reports within 48 hours.
- Fixes will be prepared on private branches and deployed promptly.
