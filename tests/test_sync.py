import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from scripts.sync_drive import read_rows, HEADERS, drive_id, build_catalog, ensure_descendant

class Reply:
    def __init__(self, value): self.value=value
    def execute(self, **kwargs): return self.value

class Drive:
    def __init__(self, parents=None): self.parents=parents or {'album123456':['root1234567']}
    def files(self): return self
    def get(self, fileId, **kwargs): return Reply({'mimeType':'application/vnd.google-apps.folder','parents':self.parents.get(fileId,[])})
    def permissions(self): return self
    def list(self, **kwargs): return Reply({'permissions':[{'type':'anyone','role':'reader'}]})

class LibraryTests(unittest.TestCase):
    def row(self, **changes):
        r=dict(id='evento',publicar='SIM',nome='Evento',data='2026-10-10',descrição='<script>alert(1)</script>',pasta='album123456',capa='')
        r.update(changes)
        return [r[h] for h in HEADERS]
    def test_rows(self):
        self.assertEqual(read_rows([HEADERS,[],self.row(publicar='NÃO')]),[])
        row=read_rows([HEADERS,self.row()])[0]
        self.assertEqual(row['description'],'<script>alert(1)</script>')
        for rows in ([HEADERS,self.row(),self.row()], [HEADERS,self.row(data='2026-02-30')], [HEADERS,self.row(publicar='talvez')], [HEADERS,self.row(id='../escape')]):
            with self.assertRaises(ValueError): read_rows(rows)
    def test_boundary(self):
        ensure_descendant(Drive(),'album123456','root1234567')
        with self.assertRaises(ValueError):ensure_descendant(Drive(),'outside12345','root1234567')
        with self.assertRaises(ValueError):ensure_descendant(Drive(),'root1234567','root1234567')
        with self.assertRaises(ValueError):drive_id('https://evil.example/folders/album123456')
    def test_sync_add_change_remove_and_cover(self):
        raw=io.BytesIO();Image.new('RGB',(30,20),'red').save(raw,'PNG')
        row=read_rows([HEADERS,self.row()])[0]
        a={'id':'image123456','name':'01.png','mimeType':'image/png'}
        b={'id':'image234567','name':'02.png','mimeType':'image/png'}
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)
            for files,count in [([a],1),([a,b],2),([b],1),([],0)]:
                with patch('scripts.sync_drive.list_media',return_value=files):
                    e=build_catalog([row],Drive(),out,'root1234567',lambda _:raw.getvalue())['editions'][0]
                    self.assertEqual(len(e['media']),count)
                    self.assertEqual(e['cover']['id'] if count else None,files[0]['id'] if count else None)
            with patch('scripts.sync_drive.list_media',return_value=[a]):
                with self.assertRaises(ValueError):build_catalog([row|{'cover_id':'image234567'}],Drive(),out,'root1234567',lambda _:raw.getvalue())
    def test_video_and_read_failure(self):
        row=read_rows([HEADERS,self.row()])[0]
        with tempfile.TemporaryDirectory() as tmp:
            with patch('scripts.sync_drive.list_media',return_value=[{'id':'video123456','name':'Vídeo','mimeType':'video/mp4'}]):
                e=build_catalog([row],Drive(),Path(tmp),'root1234567',lambda _:None)['editions'][0]
                self.assertIsNone(e['cover']);self.assertTrue(e['media'][0]['preview'].endswith('/preview'))
            with patch('scripts.sync_drive.list_media',side_effect=RuntimeError('unavailable')):
                with self.assertRaises(RuntimeError):build_catalog([row],Drive(),Path(tmp),'root1234567',lambda _:None)

if __name__=='__main__': unittest.main()
