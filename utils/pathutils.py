# -*- coding: utf-8 -*-

import string
import core.tree as tree

def createPath(parent_node, sPath, sSeparator='/'):
    dirs=string.split(sPath, sSeparator)
    for dirName in dirs:
        if len(dirName)>0:
            dir_node=tree.Node(name=dirName, type='directory')
            parent_node.addChild(dir_node)
            parent_node=dir_node
    return parent_node

def createPathPreserve(parent_node, sPath, sSeparator='/'):
    dirs=string.split(sPath, sSeparator)
    for dirName in dirs:
        if len(dirName)>0:
            try:
                node=parent_node.getChild(dirName)
                parent_node=node
            except tree.NoSuchNodeError,e:
                dir_node=tree.Node(name=dirName, type='directory')
                parent_node.addChild(dir_node)
                parent_node=dir_node
    return parent_node

def createPathPreserve2(parent_node, sPath, sType='directory', sSeparator='/'):
    dirs=string.split(sPath, sSeparator)
    for dirName in dirs:
        if len(dirName)>0:
            try:
                node=parent_node.getChild(dirName)
                parent_node=node
            except tree.NoSuchNodeError,e:
                dir_node=tree.Node(name=dirName, type=sType)
                parent_node.addChild(dir_node)
                parent_node=dir_node
    return parent_node

def checkPath(parent_node, sPath, sSeparator='/'):
    dirs=string.split(sPath, sSeparator)
    for dirName in dirs:
        if len(dirName)>0:
            try:
                parent_node=parent_node.getChild(dirName)
            except tree.NoSuchNodeError,e:
                return None
    return parent_node

# scaled down version of web.frontend.contend.getPaths() to get all paths
def getBrowsingPathList(node):
    list = []
    def r(node, path):
        if node is tree.getRoot():
            return
        for p in node.getParents():
            path.append(p)
            if p is not tree.getRoot("collections"):
                r(p, path)
        return path

    paths = []

    p = r(node, [])
    omit = 0

    if p:
        for node in p:
            if True:
                if node.type in ("directory", "home", "collection"):
                    paths.append(node)
                if node is tree.getRoot("collections") or node.type=="root":
                    paths.reverse()
                    if len(paths)>1 and not omit:
                        list.append(paths)
                    omit = 0
                    paths =[]
            else:
                omit = 1
    if len(list)>0:
        return list
    else:
        return []

def isDescendantOf(node, parent):
    if node == parent:
        return 1
    for p in node.getParents():
        if isDescendantOf(p, parent):
            return 1
    return 0