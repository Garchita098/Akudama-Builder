#!/usr/bin/env python3
"""Atomic multi-file GitHub commit. Uses GITHUB_TOKEN from the environment.
Usage: python tools/batch_commit.py changes.json
changes.json: {"message":"...","files":{"path/to/file":"full new text"}}
Never put access tokens in the JSON or commit them.
"""
import base64, json, os, sys, urllib.error, urllib.request

def api(method,path,payload=None):
    repo=os.environ["GITHUB_REPOSITORY"]
    token=os.environ["GITHUB_TOKEN"]
    data=None if payload is None else json.dumps(payload).encode()
    req=urllib.request.Request("https://api.github.com/repos/"+repo+path,data=data,method=method,headers={
        "Authorization":"Bearer "+token,"Accept":"application/vnd.github+json",
        "X-GitHub-Api-Version":"2022-11-28","Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=30) as res:
        return json.load(res)

def main():
    changes=json.load(open(sys.argv[1],encoding="utf-8"))
    files=changes["files"]
    if not files or len(files)>150: raise ValueError("Expected 1-150 files")
    branch=changes.get("branch","main")
    head=api("GET","/git/ref/heads/"+branch)["object"]["sha"]
    base=api("GET","/git/commits/"+head)["tree"]["sha"]
    entries=[]
    for path,content in files.items():
        if path.startswith("/") or ".." in path.split("/") or path.startswith(".git/"):
            raise ValueError("Invalid path "+path)
        if not isinstance(content,str): raise ValueError("Contents must be UTF-8 text")
        entries.append({"path":path,"mode":"100644","type":"blob","content":content})
    tree=api("POST","/git/trees",{"base_tree":base,"tree":entries})["sha"]
    commit=api("POST","/git/commits",{"message":changes["message"],"tree":tree,"parents":[head]})["sha"]
    api("PATCH","/git/refs/heads/"+branch,{"sha":commit,"force":False})
    print("Committed",len(entries),"files in one commit:",commit)

if __name__=="__main__":
    if len(sys.argv)!=2: sys.exit("Usage: batch_commit.py changes.json")
    main()
