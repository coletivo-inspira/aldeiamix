"""Build the public catalog from a read-only Google Drive library.

Output is staging-only: a failed run must never be deployed.
"""
import argparse
import datetime as dt
import io
import json
import os
from pathlib import Path
import re
import shutil
from urllib.parse import urlparse

HEADERS = ['id', 'publicar', 'nome', 'data', 'descrição', 'pasta', 'capa']
FOLDER = 'application/vnd.google-apps.folder'
IMAGES = {'image/jpeg', 'image/png', 'image/webp'}
MAX_IMAGE_BYTES = 25 * 1024 * 1024


def drive_id(value):
    value = str(value).strip()
    if re.fullmatch(r'[A-Za-z0-9_-]{10,}', value):
        return value
    parsed = urlparse(value)
    if parsed.scheme != 'https' or parsed.hostname not in {'drive.google.com', 'docs.google.com'}:
        raise ValueError('Use um link válido do Google Drive.')
    match = re.search(r'/(?:folders|d)/([A-Za-z0-9_-]+)', parsed.path)
    if not match:
        raise ValueError('Link do Drive sem identificador.')
    return match.group(1)


def read_rows(values):
    if not values or [str(v).strip() for v in values[0]] != HEADERS:
        raise ValueError('A primeira linha deve conter: ' + ', '.join(HEADERS))
    result, seen = [], set()
    for number, row in enumerate(values[1:], 2):
        if not any(str(x).strip() for x in row):
            continue
        row = list(row) + [''] * (7-len(row))
        ident, publish, name, date, description, folder, cover = [str(x).strip() for x in row[:7]]
        if publish.upper() not in {'SIM', 'NÃO', 'NAO', 'TRUE', 'FALSE', ''}:
            raise ValueError(f'Linha {number}: publicar deve ser SIM ou NÃO.')
        if publish.upper() not in {'SIM', 'TRUE'}:
            continue
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', ident) or ident in seen:
            raise ValueError(f'Linha {number}: id inválido ou repetido.')
        if not name or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', date):
            raise ValueError(f'Linha {number}: nome e data AAAA-MM-DD são obrigatórios.')
        dt.date.fromisoformat(date)
        seen.add(ident)
        result.append(dict(id=ident, name=name, date=date, description=description,
                           folder=drive_id(folder), cover_id=drive_id(cover) if cover else None))
    return sorted(result, key=lambda e: (e['date'], e['id']), reverse=True)


def ensure_descendant(drive, folder_id, root):
    if folder_id == root:
        raise ValueError('A edição precisa de uma subpasta própria.')
    seen, pending = set(), [folder_id]
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        item = drive.files().get(fileId=current, fields='id,mimeType,parents,trashed', supportsAllDrives=True).execute(num_retries=3)
        if item.get('trashed') or item.get('mimeType') != FOLDER:
            raise ValueError('A pasta da edição não está disponível.')
        parents = item.get('parents', [])
        if root in parents:
            return
        pending.extend(parents)
    raise ValueError('A pasta da edição está fora da biblioteca autorizada.')


def list_media(drive, folder_id):
    files, token = [], None
    while True:
        response = drive.files().list(q=f"'{folder_id}' in parents and trashed = false",
            fields='nextPageToken,files(id,name,mimeType,size,description,webViewLink)',
            pageToken=token, pageSize=100, supportsAllDrives=True, includeItemsFromAllDrives=True).execute(num_retries=3)
        files.extend(response.get('files', []))
        token = response.get('nextPageToken')
        if not token:
            break
    return sorted(files, key=lambda f: (f['name'].casefold(), f['id']))


def build_catalog(rows, drive, output, root, download):
    from PIL import Image, ImageOps
    media_dir = output / 'media'
    media_dir.mkdir(parents=True, exist_ok=True)
    editions = []
    for row in rows:
        ensure_descendant(drive, row['folder'], root)
        media = []
        for file in list_media(drive, row['folder']):
            kind = file['mimeType']
            if kind not in IMAGES | {'video/mp4'}:
                continue
            fid = file['id']
            item = dict(id=fid, name=file['name'])
            if kind in IMAGES:
                if int(file.get('size', 0)) > MAX_IMAGE_BYTES:
                    raise ValueError('Foto maior que 25 MB. Reduza o arquivo antes de publicar.')
                content = download(fid)
                if len(content) > MAX_IMAGE_BYTES:
                    raise ValueError('Foto maior que 25 MB.')
                with Image.open(io.BytesIO(content)) as original:
                    img = ImageOps.exif_transpose(original)
                    img.thumbnail((1920, 1920))
                    img = img.convert('RGB')
                    name = fid + '.webp'
                    img.save(media_dir / name, 'WEBP', quality=84)
                    item.update(type='image', src='media/'+name,
                        width=img.width, height=img.height,
                        alt=file.get('description') or f"Registro de {row['name']}")
            else:
                permissions = drive.permissions().list(fileId=fid, fields='permissions(type,role)', supportsAllDrives=True).execute(num_retries=3)
                if not any(p['type']=='anyone' for p in permissions.get('permissions', [])):
                    raise ValueError('Vídeo sem acesso público por link. Ajuste o compartilhamento no Drive.')
                item.update(type='video', preview=f'https://drive.google.com/file/d/{fid}/preview', url=f'https://drive.google.com/file/d/{fid}/view')
            media.append(item)
        photos = [m for m in media if m['type']=='image']
        cover = next((m for m in photos if m['id']==row['cover_id']), None)
        if row['cover_id'] and not cover:
            raise ValueError('A capa precisa ser uma foto da própria pasta da edição.')
        editions.append({k: row[k] for k in ('id','name','date','description')} |
                        dict(cover=cover or (photos[0] if photos else None), media=media))
    return dict(version=1, updatedAt=dt.datetime.now(dt.timezone.utc).isoformat(), editions=editions)


def prepare_site(source, output):
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    for name in ('index.html', 'edicoes.html', 'logo-aldeia.svg'):
        shutil.copy2(source/name, output/name)
    shutil.copytree(source/'assets', output/'assets')
    (output/'data').mkdir()
    (output/'.nojekyll').touch()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='_site')
    parser.add_argument('--bootstrap-empty', action='store_true', help='Explicit first deployment only; never a fallback for failed sync.')
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1]
    config = json.loads((source/'library.json').read_text())
    output = Path(args.output).resolve()
    prepare_site(source, output)
    if args.bootstrap_empty:
        catalog = dict(version=1, editions=[])
    else:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseDownload
        raw = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
        if not raw:
            raise ValueError('Configure o segredo GOOGLE_SERVICE_ACCOUNT_JSON antes de ativar a sincronização.')
        info = json.loads(raw)
        credentials = service_account.Credentials.from_service_account_info(info, scopes=[
            'https://www.googleapis.com/auth/drive.readonly', 'https://www.googleapis.com/auth/spreadsheets.readonly'])
        drive = build('drive', 'v3', credentials=credentials, cache_discovery=False)
        sheets = build('sheets', 'v4', credentials=credentials, cache_discovery=False)
        values = sheets.spreadsheets().values().get(spreadsheetId=config['spreadsheetId'], range="'Edições'!A:G", valueRenderOption='FORMATTED_VALUE').execute(num_retries=3).get('values', [])
        rows = read_rows(values)
        def download(fid):
            data = io.BytesIO()
            downloader = MediaIoBaseDownload(data, drive.files().get_media(fileId=fid), chunksize=1024*1024)
            done = False
            while not done:
                _, done = downloader.next_chunk(num_retries=3)
                if data.tell()>MAX_IMAGE_BYTES:
                    raise ValueError('Foto maior que 25 MB.')
            return data.getvalue()
        catalog = build_catalog(rows, drive, output, config['folderId'], download)
    (output/'data'/'editions.json').write_text(json.dumps(catalog, ensure_ascii=False), encoding='utf-8')
    print(f"Catálogo validado: {len(catalog['editions'])} edições.")


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Avoid printing API request URLs, credentials or tokens from third-party exceptions.
        if isinstance(error, ValueError):
            print(f'Falha de validação: {error}')
        else:
            print(f'Falha ao sincronizar ({type(error).__name__}). A publicação anterior será mantida.')
        raise SystemExit(1)
