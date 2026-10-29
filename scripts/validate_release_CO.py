"""Validate this standalone release using only the Python standard library."""
from pathlib import Path
from urllib.parse import unquote, urlsplit
import argparse
import hashlib
import json
import re
import sys

PUBLIC = 'hehe-research-project-planning'
OPTIONAL = {'hehe-report-writing', 'hehe-report-presentation'}
TEXT = {'.md', '.json', '.py', '.txt', '.html', '.svg', '.yaml', '.yml', '.css', '.js'}
FORBIDDEN = {'__pycache__', '_本地维护', '90_历史备份', '.venv'}
SKILL_REF = re.compile(r'(?<![A-Za-z0-9-])hehe-[a-z0-9]+(?:-[a-z0-9]+)*(?![A-Za-z0-9-])')
LOCAL_LINK = re.compile(r'!?\[[^\]]*\]\(([^)]+)\)|(?:href|src)=["\x27]([^"\x27]+)["\x27]')


def validate(repo):
    errors = []
    for name in ['README.md', 'LICENSE', 'CHANGELOG.md', 'requirements-pdf.txt', 'release-manifest.json']:
        if not (repo / name).is_file():
            errors.append('Missing release file: ' + name)
    if errors:
        return errors
    manifest = json.loads((repo / 'release-manifest.json').read_text(encoding='utf-8-sig'))
    runtime = repo / 'skills' / PUBLIC
    if manifest.get('entry_skill') != PUBLIC or manifest.get('required_skills') != []:
        errors.append('Invalid standalone entry or mandatory Skill dependencies')
    optional = manifest.get('optional_external_skills', {})
    if set(optional) != OPTIONAL or any(not isinstance(v, str) or not v.strip() for v in optional.values()):
        errors.append('Optional Skill declarations are incomplete')
    if sorted(p.parent.name for p in repo.rglob('SKILL.md') if '.git' not in p.parts) != [PUBLIC]:
        errors.append('The repository must contain exactly one installable Skill')
    skills = manifest.get('skills', [])
    if len(skills) != 1 or skills[0].get('name') != PUBLIC:
        return errors + ['Invalid runtime inventory']
    required = set(skills[0].get('required_files', []))
    actual = {p.relative_to(runtime).as_posix() for p in runtime.rglob('*') if p.is_file()}
    if actual != required or 'SKILL.md' not in required:
        errors.append('Runtime file inventory mismatch')
    for name in required:
        path = (runtime / name).resolve()
        if not path.is_relative_to(runtime.resolve()) or not path.is_file():
            errors.append('Missing or unsafe runtime file: ' + name)
            continue
        if hashlib.sha256(path.read_bytes()).hexdigest() != manifest.get('public_sha256', {}).get(name):
            errors.append('Runtime hash mismatch: ' + name)
        text = path.read_text(encoding='utf-8-sig')
        unknown = set(SKILL_REF.findall(text)) - OPTIONAL - {PUBLIC}
        if unknown:
            errors.append(f'Undeclared external Skill in {name}: {sorted(unknown)}')
        for private_name in ['research-project-planning', 'report-writing', 'report-presentation']:
            if re.search(r'(?<![A-Za-z0-9-])' + private_name + r'(?![A-Za-z0-9-])', text):
                errors.append('Unconverted Skill name in ' + name)
    skill_text = (runtime / 'SKILL.md').read_text(encoding='utf-8-sig')
    if not re.search(r'^name: ' + PUBLIC + r'\s*$', skill_text, re.M):
        errors.append('Frontmatter name mismatch')
    for path in repo.rglob('*'):
        rel = path.relative_to(repo)
        if '.git' in rel.parts:
            continue
        if any(part in FORBIDDEN for part in rel.parts) or path.suffix == '.pyc':
            errors.append('Forbidden release path: ' + rel.as_posix())
        if not path.is_file() or path.suffix.lower() not in TEXT:
            continue
        text = path.read_text(encoding='utf-8-sig')
        # Source for this validator contains its own forbidden-path literals.
        if rel.as_posix() != 'scripts/validate_release_CO.py':
            if re.search(r'[A-Z]:[/\\](?:Users|LenovoSoftstore)|file:///|gh[pousr]_[A-Za-z0-9]{20,}', text, re.I):
                errors.append('Private local path or credential pattern: ' + rel.as_posix())
        if path.suffix.lower() not in {'.md', '.html', '.svg'}:
            continue
        for match in LOCAL_LINK.finditer(text):
            raw = (match.group(1) or match.group(2)).strip().strip('<>')
            if raw.startswith(('#', 'data:', 'mailto:', 'javascript:')):
                continue
            parsed = urlsplit(raw)
            if parsed.scheme or parsed.netloc:
                continue
            target = (path.parent / unquote(parsed.path)).resolve()
            if not target.is_relative_to(repo.resolve()) or not target.exists():
                errors.append(f'Broken local link: {rel.as_posix()} -> {raw}')
            if path.is_relative_to(runtime) and not target.is_relative_to(runtime.resolve()):
                errors.append(f'Package-external file dependency: {rel.as_posix()} -> {raw}')
    for name in manifest.get('examples', {}).get('files', []):
        if not (repo / name).is_file():
            errors.append('Missing example: ' + name)
    return errors


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo', nargs='?', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    issues = validate(args.repo.resolve())
    for issue in issues:
        print('ERROR:', issue)
    if not issues:
        print('Release valid: one standalone Skill; files, hashes, optional references and local links checked.')
    sys.exit(bool(issues))
