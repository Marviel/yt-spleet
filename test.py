import os
import shutil

root_path = os.path.abspath('output-COPY')


for dirname in os.listdir(root_path):
    dirpath = os.path.join(root_path, dirname)
    # Go through all subfolders
    # Rename output files so that they're shorter and uniform.
    for fname in os.listdir(dirpath):
        new_fname = fname
        if fname.startswith('accompaniment'):
            new_fname = f'yts-acc_{dirname}.mp3'
        elif fname.startswith('vocals'):
            new_fname = f'yts-vox_{dirname}.mp3'

        print(f"{dirpath}: changing to {new_fname}")

        if (fname != new_fname):
            shutil.move(os.path.join(dirpath, fname),
                        os.path.join(dirpath, new_fname))
