import glob
import io
import os
import sys

# Cheap hack to make the release for manage_packages.py cleaner
try:
    import tools.tmpfile as tmpfile
except:
    import tmpfile

if 'tqdm' in sys.modules:
    # Due to tqdm(?), ifstools to become really bloated because the multiprocessing Pool never ends after the process should clean up
    del sys.modules['tqdm']


### Temporary hack until this patch makes it upstream
import ifstools.ifs
from ifstools.ifs import IFS
from ifstools.handlers import MD5Folder
import itertools
from multiprocessing import Pool
from tqdm import tqdm

def _repack_tree(self, progress = True, **kwargs):
    folders = self.tree.all_folders
    files = self.tree.all_files

    # Can't pickle lmxl, so to dirty-hack land we go
    kbin_backup = []
    for folder in folders:
        if isinstance(folder, MD5Folder):
            kbin_backup.append(folder.info_kbin)
            folder.info_kbin = None

    needs_preload = (f for f in files if f.needs_preload or not kwargs['use_cache'])
    args = list(zip(needs_preload, itertools.cycle((kwargs,))))
    p = Pool()
    for f in tqdm(p.imap_unordered(ifstools.ifs._load, args), desc='Caching', total=len(args), disable = not progress):
        if progress:
            tqdm.write(f)

    p.close()
    p.terminate()

    # restore stuff from before
    for folder in folders:
        if isinstance(folder, MD5Folder):
            folder.info_kbin = kbin_backup.pop(0)

    tqdm_progress = None
    if progress:
        tqdm_progress = tqdm(desc='Writing', total=len(files))
    self.tree.repack(self.manifest.xml_doc, self.data_blob, tqdm_progress, **kwargs)

    return self.data_blob.getvalue()
### Temporary hack until this patch makes it upstream


def extract(filename, path=None, progress=False):
    if not path:
        path = tmpfile.mkdtemp(prefix="ifs")

    ifs = IFS(filename)
    ifs.extract(progress=progress, path=path)
    del ifs

    # Get file list
    return glob.glob(os.path.join(path, "*")), path

def create(foldername, output_filename, progress=False):
    ifs = IFS(foldername)
    setattr(IFS, ifs._repack_tree.__name__, _repack_tree) ### Temporary hack until this patch makes it upstream
    ifs.repack(progress=progress, path=output_filename, use_cache=True)
    del ifs

    return output_filename
