#!/usr/bin/env python

import imp
import logging
import os
import ply.yacc

from splparser.parsetree import *
from splparser.exceptions import SPLSyntaxError

from splparser.cmdparsers.common.asrules import *
from splparser.cmdparsers.common.byrules import *
from splparser.cmdparsers.common.simplefieldrules import *
from splparser.cmdparsers.common.simplefieldlistrules import *
from splparser.cmdparsers.common.statsfnrules import *

from splparser.cmdparsers.statslexer import lexer, precedence, tokens

PARSETAB_DIR = 'parsetabs'
PARSETAB = 'stats_parsetab'

start = 'cmdexpr'

# NOTE: The strange structure of these rules is because we need to always
#       associate STATS_FN with another token on the RHS of rules because
#       otherwise we get a reduce/reduce conflict from the rule
#           simplefield : STATS_FN
#       since nothing prevents simplefields from having the same name as command
#       functions.
# NOTE: Now that the parser has been refactored from the monolith model to
#       a confederation of decentralized parsers model, the above is 
#       probably no longer true.

def p_cmdexpr_stats(p):
    """cmdexpr : statscmd"""
    p[0] = p[1]

def p_statscmd(p):
    """statscmd : statscmdstart"""
    p[0] = p[1]

def p_statscmd_cont(p):
    """statscmd : statscmdstart statscmdcont"""
    p[0] = p[1]
    p[0].add_children(p[2].children)

def p_statscmdstart(p):
    """statscmdstart : STATS STATS_FN
                     | STATS COMMON_FN  
                     | STATS EVAL
                     | STATS statsoptlist STATS_FN
                     | STATS statsoptlist COMMON_FN
                     | STATS statsoptlist EVAL"""
    p[0] = ParseTreeNode('STATS')
    fn_idx = 2
    if len(p) > 3:
        fn_idx = 3
        p[0].add_children(p[2].children)
    fn_node = ParseTreeNode(p[fn_idx].upper())
    p[0].add_child(fn_node)

def p_statsoptlist(p):
    """statsoptlist : statsopt"""
    p[0] = ParseTreeNode('_STATS_OPT_LIST')
    p[0].add_child(p[1])

def p_statsoptlist_statsopt(p):
    """statsoptlist : statsopt statsoptlist"""
    p[0] = ParseTreeNode('_STATS_OPT_LIST')
    p[0].add_child(p[1])
    p[0].add_children(p[2].children)

def p_statsopt_simplefield(p):
    """statsopt : STATS_OPT EQ simplefield"""
    p[0] = ParseTreeNode(p[1].upper())
    p[0].add_child(p[3])

def p_statsopt_delimiter(p):
    """statsopt : STATS_OPT EQ COMMA"""
    p[0] = ParseTreeNode(p[1].upper())
    comma_node = ParseTreeNode('COMMA')
    p[0].add_child(comma_node)

def p_statscmdstart_asbylist(p):
    """statscmdstart : STATS STATS_FN asbylist
                     | STATS COMMON_FN asbylist
                     | STATS EVAL asbylist
                     | STATS statsoptlist STATS_FN asbylist
                     | STATS statsoptlist COMMON_FN asbylist
                     | STATS statsoptlist EVAL asbylist"""
    p[0] = ParseTreeNode('STATS')
    fn_idx = 2
    if len(p) > 4:
        fn_idx = 3
        p[0].add_children(p[2].children)
    asby_idx = fn_idx + 1
    fn_node = ParseTreeNode(p[fn_idx].upper())
    fn_node.add_children(p[asby_idx].children)
    p[0].add_child(fn_node)

def p_statscmdstart_statsfnexpr(p):
    """statscmdstart : STATS statsfnexpr
                     | STATS statsoptlist statsfnexpr"""
    p[0] = ParseTreeNode('STATS')
    fn_idx = 2
    if len(p) > 3:
        fn_idx = 3
        p[0].add_children(p[2].children)
    p[0].add_children(p[fn_idx].children)

def p_statscmdstart_statsfnexpr_asbylist(p):
    """statscmdstart : STATS statsfnexpr asbylist
                     | STATS statsoptlist statsfnexpr asbylist"""
    p[0] = ParseTreeNode('STATS')
    fn_idx = 2
    if len(p) > 4:
        fn_idx = 3
        p[0].add_children(p[2].children)
    asby_idx = fn_idx + 1
    p[fn_idx].children[0].add_children(p[asby_idx].children)
    p[0].add_children(p[fn_idx].children)
    #p[0].children[0].add_children(p[asby_idx].children)

def p_statscmdcont_statscmdcont(p):
    """statscmdcont : statscmdcont statscmdcont"""
    p[0] = ParseTreeNode('_STATSCMDCONT')
    p[0].add_children(p[1].children)
    p[0].add_children(p[2].children)

def p_statscmdcont(p):
    """statscmdcont : COMMA STATS_FN
                    | COMMA COMMON_FN
                    | COMMA EVAL"""
    p[0] = ParseTreeNode('_STATSCMDCONT')
    fn_node = ParseTreeNode(p[2].upper())
    p[0].add_child(fn_node)

def p_statscmdcont_statsfnexpr(p):
    """statscmdcont : COMMA statsfnexpr"""
    p[0] = ParseTreeNode('_STATSCMDCONT')
    p[0].add_children(p[2].children)

def p_statsfnexpr_stats_fn(p):
    """statsfnexpr : STATS_FN asbylist
                   | COMMON_FN asbylist"""
    p[0] = ParseTreeNode('_STATSFNEXPR')
    fn_node = ParseTreeNode(p[1].upper())
    p[0].add_child(fn_node)
    p[0].children[0].add_children(p[2].children)

def p_statsfnexpr_asbylist(p):
    """statsfnexpr : statsfnexpr asbylist"""
    p[0] = ParseTreeNode('_STATSFNEXPR')
    p[0].add_children(p[1].children)
    p[0].children[0].add_children(p[2].children)

def p_asbylist_as(p):
    """asbylist : as simplefield"""
    p[0] = ParseTreeNode('_ASBYLIST')
    as_node = ParseTreeNode('AS')
    p[0].add_child(as_node)
    as_node.add_child(p[2])

def p_asbylist_by(p):
    """asbylist : by simplefieldlist"""
    p[0] = ParseTreeNode('_ASBYLIST')
    by_node = ParseTreeNode('BY')
    p[0].add_child(by_node)
    by_node.add_children(p[2].children)

def p_asbylist(p):
    """asbylist : as simplefield by simplefieldlist"""
    p[0] = ParseTreeNode('_ASBYLIST')
    as_node = ParseTreeNode('AS')
    by_node = ParseTreeNode('BY')
    p[0].add_child(as_node)
    as_node.add_child(p[2])
    p[0].add_child(by_node)
    by_node.add_children(p[4].children)
def p_error(p):
    raise SPLSyntaxError("Syntax error in stats parser input!") 

logging.basicConfig(
    level = logging.DEBUG,
    filename = "statsparser.log",
    filemode = "w",
    format = "%(filename)10s:%(lineno)4d:%(message)s"
)

log = logging.getLogger()

def parse(data, ldebug=False, ldebuglog=log, pdebug=False, pdebuglog=log):
    here = os.path.dirname(__file__)
    path_to_parsetab = os.path.join(here, PARSETAB_DIR, PARSETAB + '.py')
    
    try:
        parsetab = imp.load_source(PARSETAB, path_to_parsetab)
    except IOError: # parsetab files don't exist in our installation
        parsetab = PARSETAB

    try:
        os.stat(PARSETAB_DIR)
    except:
        try:
            os.makedirs(PARSETAB_DIR)
        except OSError:
            sys.stderr.write("ERROR: Need permission to write to ./" + PARSETAB_DIR + "\n")
            raise

    parser= ply.yacc.yacc(debug=pdebug, debuglog=pdebuglog, tabmodule=parsetab, outputdir=PARSETAB_DIR)
    return parser.parse(data, debug=pdebuglog, lexer=lexer)

if __name__ == "__main__":
    import sys
    lexer = ply.lex.lex()
    parser = ply.yacc.yacc()
    print parser.parse(sys.argv[1:], debug=log, lexer=lexer)
