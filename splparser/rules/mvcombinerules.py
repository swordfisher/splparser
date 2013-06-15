#!/usr/bin/env python

from splparser.parsetree import *

from splparser.rules.common.fieldrules import *
from splparser.rules.common.fieldlistrules import *
from splparser.rules.common.valuerules import *

from splparser.lexers.mvcombinelexer import tokens
from splparser.exceptions import SPLSyntaxError

start = 'cmdexpr'

def p_cmdexpr_fillnull(p):
    """cmdexpr : mvcombinecmd"""
    p[0] = p[1]

def p_fillnullcmd_fillnull(p):
    """mvcombinecmd : MVCOMBINE"""
    p[0] = ParseTreeNode('MVCOMBINE')

def p_fillnullcmd_value(p):
    """mvcombinecmd : MVCOMBINE field"""
    p[0] = ParseTreeNode('MVCOMBINE')
    p[0].add_child(p[2])

def p_fieldlist(p):
    """mvcombinecmd : MVCOMBINE m_delim field"""
    p[0] = ParseTreeNode('MVCOMBINE')
    p[0].add_children([p[2],p[3]])

def p_value(p):
    """m_delim : DELIM EQ value"""
    p[0] = ParseTreeNode('EQ')
    p[1] = ParseTreeNode(p[1].upper(), option=True)
    p[1].values.append(p[3])
    p[0].add_children([p[1],p[3]])

def p_comma(p):
    """m_delim : DELIM EQ COMMA"""
    p[0] = ParseTreeNode('EQ')
    p[1] = ParseTreeNode(p[1].upper())
    p[3] = ParseTreeNode(p[3])
    p[0].add_children([p[1],p[3]])

def p_error(p):
    raise SPLSyntaxError("Syntax error in mvcombine parser input!") 