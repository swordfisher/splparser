#!/usr/bin/env python

import json

from . import schema

from itertools import chain

INDENT = '    '

class ParseTreeNode(object):
    
    def __init__(self, type, raw="", associative=False, arg=False, expr=False, field=False, option=False, renamed=None, value=False):
        """
        >>> p = ParseTreeNode('TYPE', raw="raw")
        >>> p.type
        'TYPE'
        >>> p.raw
        'raw'
        >>> p.children
        []
        >>> p.parent
        >>> p = ParseTreeNode()
        Traceback (most recent call last):
          File "<stdin>", line 1, in <module>
        TypeError: __init__() takes at least 2 arguments (1 given)
        """
        
        self.type = type
        self.raw = raw
        self.parent = None
        self.children = []

        self.label = self.type.lower()
        #if not raw == '':
        #    self.label = self.type
        
        self.associative = associative
        
        self.arg = arg
        self.expr = expr
        self.field = field
        self.option = option
        self.renamed = renamed
        self.value = value
        self.values = []

    def __eq__(self, other):
        #print "I am ", self.type, self.raw
        if len(self.children) == 0 and len(other.children) == 0:
            eq = self._node_eq(other)
            #print "No children and eq is:", eq
            return eq
        if (len(self.children) == 0 and not len(other.children) == 0) or \
            (not len(self.children) == 0 and len(other.children) == 0):
            #print "One has children and the other doesn't"
            return False
        return all([self_child == other_child for (self_child, other_child) in zip(self.children, other.children)])

    def _node_eq(self, other):
        return self.type == other.type and self.raw == other.raw

    def is_supertree_of(self, other):
        #print "I am ", self.type, self.raw
        if other is None:
            #print "other is None"
            return True
        if len(self.children) >= 0 and len(other.children) == 0:
            eq = self._node_eq(other)
            #print "other is childless and eq is", eq
            return eq
        if len(self.children) == 0 and len(other.children) > 0:
            #print "other has more children than me 1"
            return False
        if len(self.children) < len(other.children):
            #print "other has more children than me 2"
            return False
        if len(self.children) > 0 and len(other.children) > 0:
            #print "other and I are comparing children"
            ocidx = 0
            children_eq = True
            for child in self.children:
                if ocidx >= len(other.children):
                    break
                if child._node_eq(other.children[ocidx]):
                    children_eq = children_eq and child.is_supertree_of(other.children[ocidx])
                    #print "children_eq is", children_eq
                    ocidx += 1
            if len(other.children) > ocidx + 1:
                return False
            return self._node_eq(other) and children_eq

    @staticmethod
    def from_dict(d):
        p = ParseTreeNode("")
        p.type = str(d['type'])
        p.label = p.type.lower()
        p.raw = str(d['raw'])
        p.associative = bool(d['associative'])
        p.arg = bool(d['arg'])
        p.add_children([ParseTreeNode.from_dict(c) for c in d['children']])
        return p

    def template(self):
        children = map(lambda x: x.template(), self.children) 
        if self.arg:
            p = ParseTreeNode('', arg=True, expr=self.expr, field=self.field, option=self.option, renamed=self.renamed, value=self.value)
        else:
            p = ParseTreeNode(self.type, raw=self.raw, associative=self.associative, expr=self.expr, field=self.field, option=self.option, renamed=self.renamed, value=self.value)
        p.add_children(children)
        return p

    def inverse_template(self):
        children = map(lambda x: x.inverse_template(), self.children) 
        if not self.arg:
            p = ParseTreeNode('', arg=False, expr=self.expr, field=self.field, option=self.option, renamed=self.renamed, value=self.value)
        else:
            p = ParseTreeNode(self.type, raw=self.raw, associative=self.associative, arg=True, expr=self.expr, field=self.field, option=self.option, renamed=self.renamed, value=self.value)
        p.add_children(children)
        return p

    def command_arg_tuple_list(self):
        stages = self._stage_subtrees()
        command_and_args = [stage._command_arg_tuple_from_stage() for stage in stages]
        return command_and_args

    def _stage_subtrees(self):
        if not self.type == 'ROOT':
            raise ValueError("This must be 'ROOT' node for this to work properly.\n")
        return self.children

    def _command_arg_tuple_from_stage(self):
        if not self.type == 'STAGE':
            raise ValueError("This must be 'STAGE' node for this to work properly.\n")
        command = self.children[0].template()._flatten_to_string()
        args = self.children[0].inverse_template()._flatten_to_list()
        return (command, args)

    def _flatten_to_string(self):
        flattened_children = [child._flatten_to_string() for child in self.children]
        flattened_children = filter(lambda x: not x == '()', flattened_children)
        children_string = ','.join(flattened_children)
        children_string = ''.join(['(', children_string, ')'])
        if self.type == '':
            return children_string
        if children_string == '()':
            return self.type
        return ''.join([self.type, children_string])

    def _flatten_to_list(self):
        children_list = list(chain.from_iterable([child._flatten_to_list() for child in self.children]))
        if self.raw == '':
            return children_list
        field = (self.field and not self.option)
        return [(self.raw, field)] + children_list

    def add_child(self, child):
        if self.associative and child.type == self.type and len(child.children) > 0:
            self.add_children(child.children)
        else:
            self.children.append(child)
        for child in self.children:
            child.parent = self
    
    def add_children(self, children):
        """
        >>> p = ParseTreeNode('PARENT')
        >>> x = ParseTreeNode('CHILD', raw="x")
        >>> p.add_child(x)
        >>> a = ParseTreeNode('CHILD', raw="a")
        >>> b = ParseTreeNode('CHILD', raw="b")
        >>> c = ParseTreeNode('CHILD', raw="c")
        >>> x.add_children([a, b, c])
        >>> y = ParseTreeNode('CHILD', raw="y")
        >>> p.add_child(y)
        >>> p.children
        [{type: 'CHILD', raw: 'x', children: [('CHILD': 'a'), ('CHILD': 'b'), ('CHILD': 'c')], parent: ('PARENT')}, {type: 'CHILD', raw: 'y', children: [], parent: ('PARENT')}]
        >>> x.children
        [{type: 'CHILD', raw: 'a', children: [], parent: ('CHILD': 'x')}, {type: 'CHILD', raw: 'b', children: [], parent: ('CHILD': 'x')}, {type: 'CHILD', raw: 'c', children: [], parent: ('CHILD': 'x')}]
        """
        for child in children:
            self.add_child(child)
    
    def remove_child(self, child):
        self.children.remove(child)
        child.parent = None

    def remove_children(self, children):
        """
        >>> p = ParseTreeNode('PARENT')
        >>> x = ParseTreeNode('CHILD', raw="x")
        >>> p.add_child(x)
        >>> a = ParseTreeNode('CHILD', raw="a")
        >>> b = ParseTreeNode('CHILD', raw="b")
        >>> c = ParseTreeNode('CHILD', raw="c")
        >>> x.add_children([a, b, c])
        >>> y = ParseTreeNode('CHILD', raw="y")
        >>> p.add_child(y)
        >>> x.remove_children([a,b])
        >>> x.children
        [{type: 'CHILD', raw: 'c', children: [], parent: ('CHILD': 'x')}]
        >>> p.remove_child(y)
        >>> p.children
        [{type: 'CHILD', raw: 'x', children: [('CHILD': 'c')], parent: ('PARENT')}]
        >>> a
        {type: 'CHILD', raw: 'a', children: [], parent: None}
        >>> y
        {type: 'CHILD', raw: 'y', children: [], parent: None}
        >>> p.remove_child(y)
        Traceback (most recent call last):
          File "<stdin>", line 1, in <module>
          File "art/splparsetree.py", line 53, in remove_child
            self.children.remove(child)
        ValueError: list.remove(x): x not in list
        >>> p.add_child(x)
        >>> p.remove_child(x)
        >>> p.children
        [{type: 'CHILD', raw: 'x', children: [('CHILD': 'c')], parent: None}]
        >>> p.remove_child(x)
        >>> p.children
        []
        >>> p.add_child(x)
        >>> p.add_child(x)
        >>> p.remove_children([x, x])
        >>> p
        {type: 'PARENT', raw: '', children: [], parent: None}
        >>> x
        {type: 'CHILD', raw: 'x', children: [('CHILD': 'c')], parent: None}
        """
        tmp = []
        for child in self.children:
            if child in children:
               child.parent = None
            else:
                tmp.append(child)
        self.children = tmp        

    def clear_children(self):
        self.children = []

    def __repr__(self):
        """
        >>> p = ParseTreeNode('PARENT')
        >>> x = ParseTreeNode('CHILD', raw="x")
        >>> p.add_child(x)
        >>> a = ParseTreeNode('CHILD', raw="a")
        >>> b = ParseTreeNode('CHILD', raw="b")
        >>> c = ParseTreeNode('CHILD', raw="c")
        >>> x.add_children([a, b, c])
        >>> y = ParseTreeNode('CHILD', raw="y")
        >>> p.add_child(y)
        >>> p
        {type: 'PARENT', raw: '', children: [('CHILD': 'x'), ('CHILD': 'y')], parent: None}
        >>> x
        {type: 'CHILD', raw: 'x', children: [('CHILD': 'a'), ('CHILD': 'b'), ('CHILD': 'c')], parent: ('PARENT')}
        >>> a
        {type: 'CHILD', raw: 'a', children: [], parent: ('CHILD': 'x')}
        """
        child_repr = ''
        first = True
        for child in self.children:
            if not first:
                child_repr = ''.join([child_repr, ', ', str(child)])
            else:
                child_repr = str(child)
                first = False
        to_repr = ''.join(["{type: '", self.type,\
                            "', raw: '", self.raw,\
                            "', children: [", child_repr,\
                            "], parent: ", str(self.parent), "}"])
        return to_repr

    def __str__(self):
        """
        >>> p = ParseTreeNode('PARENT')
        >>> x = ParseTreeNode('CHILD', raw="x")
        >>> p.add_child(x)
        >>> a = ParseTreeNode('CHILD', raw="a")
        >>> b = ParseTreeNode('CHILD', raw="b")
        >>> c = ParseTreeNode('CHILD', raw="c")
        >>> x.add_children([a, b, c])
        >>> y = ParseTreeNode('CHILD', raw="y")
        >>> p.add_child(y)
        >>> print(p)
        ('PARENT')
        >>> print(x)
        ('CHILD': 'x')
        >>> print(a)
        ('CHILD': 'a')
        """
        to_str = ''.join(["('", self.type, "'"])
        if not self.raw == "":
            to_str = ''.join([to_str, ": '", self.raw, "'"])
        to_str = ''.join([to_str, ")"])
        return to_str

    def _str_tree(self, recursive=True, indent=1):
        to_str = str(self)
        to_str = ''.join([to_str])
        if recursive:
            for child in self.children:
                to_str = ''.join([to_str, '\n', INDENT*indent, child._str_tree(indent=indent+1)])
        return to_str

    def str_tree(self, recursive=True):
        return self._str_tree(recursive=recursive)

    def print_tree(self, recursive=True):
        """
        >>> p = ParseTreeNode('PARENT')
        >>> x = ParseTreeNode('CHILD', raw="x")
        >>> p.add_child(x)
        >>> p.print_tree()
        ('PARENT')
            ('CHILD': 'x')
        >>> a = ParseTreeNode('CHILD', raw="a")
        >>> b = ParseTreeNode('CHILD', raw="b")
        >>> c = ParseTreeNode('CHILD', raw="c")
        >>> x.add_children([a, b, c])
        >>> p.print_tree()
        ('PARENT')
            ('CHILD': 'x')
                ('CHILD': 'a')
                ('CHILD': 'b')
                ('CHILD': 'c')
        >>> y = ParseTreeNode('CHILD', raw="y")
        >>> p.add_child(y)
        >>> p.print_tree()
        ('PARENT')
            ('CHILD': 'x')
                ('CHILD': 'a')
                ('CHILD': 'b')
                ('CHILD': 'c')
            ('CHILD': 'y')
        >>> p.print_tree(recursive=False)
        ('PARENT')
        """
        print self.str_tree(recursive=recursive)

    def jsonify(self):
        encoding = {}
        encoding['type'] = self.type
        encoding['raw'] = self.raw
        encoding['associative'] = self.associative
        encoding['arg'] = self.arg
        encoding['children'] = []
        for child in self.children:
            encoding['children'].append(child.jsonify())
        return encoding

    class ParseTreeNodeEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, ParseTreeNode):
                return obj.jsonify()
            return json.JSONEncoder.default(self, obj)
    
    def dumps(self, **kwargs):
        return json.dumps(self, cls=self.ParseTreeNodeEncoder, **kwargs)

    def schema(self):
        field_tokens = self.extract_fields()
        fields = {}
        for field_token in field_tokens:
            if not field_token.raw in fields:
                fields[field_token.raw] = schema.Field(field_token.raw)
            field = fields[field_token.raw]
            field.values = list(set(field.values) | set([value.raw for value in field_token.values]))
        s = schema.Schema()
        s.fields = fields.values()
        
        value_tokens = self.extract_values()
        for value_token in value_tokens:
            if value_token.raw == "":
                value_token.raw = value_token.type.lower()
            present = False
            for f in s.fields:
                if value_token.raw in f.values:
                    present = True
            if not present:
                g = schema.Field("")
                g.values = [value_token.raw]
                s.fields.append(g)
        return s

    def extract_fields(self):
        stack = []
        fields = []
        stack.insert(0, self)
        while len(stack) > 0:
            node = stack.pop()
            if node.field:
                fields.append(node)
            if len(node.children) > 0:
                for c in node.children:
                    stack.insert(0, c)
        return fields
    
    def extract_values(self):
        stack = []
        values = []
        stack.insert(0, self)
        while len(stack) > 0:
            node = stack.pop()
            if node.value:
                values.append(node)
            if len(node.children) > 0:
                for c in node.children:
                    stack.insert(0, c)
        return values
