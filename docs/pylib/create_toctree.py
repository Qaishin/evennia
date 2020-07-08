"""
Build a TOC-tree; Sphinx requires it and this makes it easy to just
add/build/link new files without needing to explicitly add it to a toctree
directive somewhere.

"""

import re
from collections import defaultdict
from sphinx.errors import DocumentError
from pathlib import Path
from os.path import abspath, dirname, join as pathjoin, sep, relpath

_IGNORE_FILES = []
_SOURCEDIR_NAME = "source"
_SOURCE_DIR = pathjoin(dirname(dirname(abspath(__file__))), _SOURCEDIR_NAME)
_TOC_FILE = pathjoin(_SOURCE_DIR, "toc.md")
_NO_REMAP_STARTSWITH = ["http://", "https://", "github:", "api:",
                        "feature-request", "report-bug", "issue", "bug-report"]

TXT_REMAPS = {
    "Developer Central": "Evennia Component overview",
    "Getting Started": "Setup Quickstart",
}
URL_REMAPS = {
    "Developer-Central": "Component/Component-Overview",
    "Tutorials": "Howto/Howto-Overview",
    "../Howto/Starting/Directory-Overview": "Gamedir-Overview",
    "Howto/Starting/Directory-Overview": "Gamedir-Overview",
    "Starting/Directory-Overview": "Gamedir-Overview",
    "Directory-Overview": "Gamedir-Overview",
    "../Setup/Getting-Started": "Setup-Quickstart",
    "Setup/Getting-Started": "Setup-Quickstart",
    "Getting-Started": "Setup-Quickstart",
    "First-Steps-Coding": "Starting-Part1",
    "../Howto/Starting/Adding-Command-Tutorial": "Adding-Commands",
    "Howto/Starting/Adding-Command-Tutorial": "Adding-Commands",
    "Starting/Adding-Command-Tutorial": "Adding-Commands",
    "Adding-Command-Tutorial": "Adding-Commands",
    "CmdSet": "Command-Sets",
    "Spawner": "Spawner-and-Prototypes",
    "issue": "github:issue",
    "issues": "github:issue",
    "bug": "github:issue",
    "bug-report": "github:issue",
    "Components/Components-Overview": "Component-Overview",
    "Components-Overview": "Component-Overview",
    "Concepts/Concepts-Overview": "Concept-Overview",
    "Concepts-Overview": "Concept-Overview",
}


_CURRFILE = None

def create_toctree():
    """
    Create source/toc.md file

    """
    global _CURRFILE

    def _get_rel_source_ref(path):
        """Get the path relative the source/ dir"""
        pathparts = path.split("/")
        # we allow a max of 4 levels of nesting in the source dir
        ind = pathparts[-5:].index(_SOURCEDIR_NAME)
        # get the part after source/
        pathparts = pathparts[-5 + 1 + ind:]
        url = "/".join(pathparts)
        # get the reference, without .md
        url = url.rsplit(".", 1)[0]
        return url

    toc_map = {}
    docref_map = defaultdict(dict)

    for path in Path(_SOURCE_DIR).rglob("*.md"):
        # find the source/ part of the path and strip it out

        if path.name in _IGNORE_FILES:
            # this is the name including .md
            continue

        sourcepath = path.as_posix()
        # get name and url relative to source/
        fname = path.name.rsplit(".", 1)[0]
        src_url = _get_rel_source_ref(sourcepath)

        # check for duplicate files
        if fname in toc_map:
            duplicate_src_url = toc_map[fname]
            raise DocumentError(
                f" Tried to add {src_url}.md, but a file {duplicate_src_url}.md already exists.\n"
                " Evennia's auto-link-corrector does not accept doc-files with the same \n"
                " name, even in different folders. Rename one.\n")
        toc_map[fname] = src_url

        # find relative links to all other files
        for targetpath in Path(_SOURCE_DIR).rglob("*.md"):

            targetname = targetpath.name.rsplit(".", 1)[0]
            targetpath = targetpath.as_posix()
            url = relpath(targetpath, dirname(sourcepath))
            docref_map[sourcepath][targetname] = url.rsplit(".", 1)[0]


    # normal reference-links [txt](urls)
    ref_regex = re.compile(r"\[(?P<txt>[\w -\[\]\`]+?)\]\((?P<url>.+?)\)", re.I + re.S + re.U + re.M)
    # in document references
    ref_doc_regex = re.compile(r"\[(?P<txt>[\w -\`]+?)\]:\s+?(?P<url>.+?)(?=$|\n)", re.I + re.S + re.U + re.M)

    def _sub(match):
        # inline reference links
        grpdict = match.groupdict()
        txt, url = grpdict['txt'], grpdict['url']

        txt = TXT_REMAPS.get(txt, txt)
        url = URL_REMAPS.get(url, url)

        if any(url.startswith(noremap) for noremap in _NO_REMAP_STARTSWITH):
            return f"[{txt}]({url})"

        if "http" in url and "://" in url:
            urlout = url
        else:
            fname, *part = url.rsplit("/", 1)
            fname = part[0] if part else fname
            fname = fname.rsplit(".", 1)[0]
            fname, *anchor = fname.rsplit("#", 1)
            if _CURRFILE in docref_map and fname in docref_map[_CURRFILE]:
                urlout = docref_map[_CURRFILE][fname] + ('#' + anchor[0] if anchor else '')
                if urlout != url:
                    print(f"  Remapped link [{txt}]({url}) -> [{txt}]({urlout})")
            else:
                urlout = url
        return f"[{txt}]({urlout})"

    def _sub_doc(match):
        # reference links set at the bottom of the page
        grpdict = match.groupdict()
        txt, url = grpdict['txt'], grpdict['url']

        txt = TXT_REMAPS.get(txt, txt)
        url = URL_REMAPS.get(url, url)

        if any(url.startswith(noremap) for noremap in _NO_REMAP_STARTSWITH):
            return f"[{txt}]({url})"

        if "http" in url and "://" in url:
            urlout = url
        else:
            fname, *part = url.rsplit("/", 1)
            fname = part[0] if part else fname
            fname = fname.rsplit(".", 1)[0]
            fname, *anchor = fname.rsplit("#", 1)
            if _CURRFILE in docref_map and fname in docref_map[_CURRFILE]:
                urlout = docref_map[_CURRFILE][fname] + ('#' + anchor[0] if anchor else '')
                if urlout != url:
                    print(f"  Remapped link [{txt}]: {url} -> [{txt}]: {urlout}")
            else:
                urlout = url
        return f"[{txt}]: {urlout}"

    # replace / correct links in all files
    count = 0
    for path in sorted(Path(_SOURCE_DIR).rglob("*.md"), key=lambda p: p.name):

        # from pudb import debugger;debugger.Debugger().set_trace()
        _CURRFILE = path.as_posix()

        with open(path, 'r') as fil:
            intxt = fil.read()
            outtxt = ref_regex.sub(_sub, intxt)
            outtxt = ref_doc_regex.sub(_sub_doc, outtxt)
        if intxt != outtxt:
            with open(path, 'w') as fil:
                fil.write(outtxt)
            count += 1
            print(f" -- Auto-relinked links in {path.name}")

    if count > 0:
        print(f"Auto-corrected links in {count} documents.")

    # write tocfile
    with open(_TOC_FILE, "w") as fil:
        fil.write("# Toc\n")

        for ref in sorted(toc_map.values()):

            if ref == "toc":
                continue

            linkname = ref.replace("-", " ")
            fil.write(f"\n- [{linkname}]({ref})")

        # we add a self-reference so the toc itself is also a part of a toctree
        fil.write("\n\n```toctree::\n  :hidden:\n\n  toc\n```")

if __name__ == "__main__":
    create_toctree()
