#! /usr/bin/env python3

# --------------------------------------------------------------------
import dataclasses as dc
import inspect
import json
import os
import re
import sys

# --------------------------------------------------------------------
class Expression:
    pass

# --------------------------------------------------------------------
@dc.dataclass
class VarExpression(Expression):
    name: str

# --------------------------------------------------------------------
@dc.dataclass
class IntExpression(Expression):
    value: int

# --------------------------------------------------------------------
@dc.dataclass
class OpAppExpression(Expression):
    operator: str
    arguments: list[Expression]

# --------------------------------------------------------------------
class Statement:
    pass

# --------------------------------------------------------------------
@dc.dataclass
class VarDeclStatement(Statement):
    name: str

# --------------------------------------------------------------------
@dc.dataclass
class AssignStatement(Statement):
    lhs: str
    rhs: Expression

# --------------------------------------------------------------------
@dc.dataclass
class PrintStatement(Statement):
    value: Expression

# --------------------------------------------------------------------
class InvalidBXJSon(Exception):
    pass

# --------------------------------------------------------------------
def check_shallow_schema(data, schema):
    if not isinstance(data, dict):
        raise InvalidBXJSon

    for name, etype in schema:
        if name not in data:
            raise InvalidBXJSon

        if etype is None:
            continue

        value = data[name]

        if isinstance(etype, str):
            if not isinstance(value, (list, tuple)):
                raise InvalidBXJSon
            if len(value) != 2:
                raise InvalidBXJSon
            if not isinstance(value[0], str):
                raise InvalidBXJSon
            if parse_tag(value[0])[0] != etype:
                raise InvalidBXJSon

            continue

        if not isinstance(value, etype):
            raise InvalidBXJSon

# --------------------------------------------------------------------
def parse_tag(tag : str) -> tuple[str, str]:
    if (m := re.search(r'^<(\w+)(?::(\w+))?>$', tag)) is None:
        raise InvalidBXJSon
    return m.group(1), m.group(2)

# --------------------------------------------------------------------
def parse_name(name) -> str:
    try:
        return name[1]['value']
    except IndexError:
        raise InvalidBXJSon

# --------------------------------------------------------------------
JSON_EXPRESSIONS = dict()

# --------------------------------------------------------------------
def expression_of_json(tag, data):
    clazz, tag = parse_tag(tag)

    if clazz != 'expression':
        raise InvalidBXJSon()

    if tag not in JSON_EXPRESSIONS:
        raise InvalidBXJSon

    check_shallow_schema(data, JSON_EXPRESSIONS[tag][0])

    return JSON_EXPRESSIONS[tag][1](data)

# --------------------------------------------------------------------
EXPRESSION_VAR_SCHEMA = [
    ('name', 'name'),
]

def expression_var_of_json(data):
    return VarExpression(name = parse_name(data['name']))

JSON_EXPRESSIONS['var'] = (
    EXPRESSION_VAR_SCHEMA, expression_var_of_json
)

# --------------------------------------------------------------------
EXPRESSION_INT_SCHEMA = [
    ('value', int),
]

def expression_int_of_json(data):
    return IntExpression(value = data['value'])

JSON_EXPRESSIONS['int'] = (
    EXPRESSION_INT_SCHEMA, expression_int_of_json
)

# --------------------------------------------------------------------
EXPRESSION_UNIOP_SCHEMA = [
    ('operator', 'name'      ),
    ('argument', 'expression'),
]

def expression_uniop_of_json(data):
    return OpAppExpression(
        operator  = parse_name(data['operator']),
        arguments = [expression_of_json(*data['argument'])],
    )

JSON_EXPRESSIONS['uniop'] = (
    EXPRESSION_UNIOP_SCHEMA, expression_uniop_of_json
)

# --------------------------------------------------------------------
EXPRESSION_BINOP_SCHEMA = [
    ('operator', 'name'      ),
    ('left'    , 'expression'),
    ('right'   , 'expression'),
]

def expression_binop_of_json(data):
    return OpAppExpression(
        operator  = parse_name(data['operator']),
        arguments = [
            expression_of_json(*data['left' ]),
            expression_of_json(*data['right']),
        ],
    )

JSON_EXPRESSIONS['binop'] = (
    EXPRESSION_BINOP_SCHEMA, expression_binop_of_json
)

# --------------------------------------------------------------------
JSON_STATEMENTS = dict()

# --------------------------------------------------------------------
def statement_of_json(tag, data):
    clazz, tag = parse_tag(tag)

    if clazz != 'statement':
        raise InvalidBXJSon

    if tag not in JSON_STATEMENTS:
        raise InvalidBXJSon

    check_shallow_schema(data, JSON_STATEMENTS[tag][0])

    return JSON_STATEMENTS[tag][1](data)

# --------------------------------------------------------------------
STATEMENT_VARDECL_SCHEMA = [
    ('name', 'name'),
]

def statement_vardecl_of_json(data):
    return VarDeclStatement(name = parse_name(data['name']))

JSON_STATEMENTS['vardecl'] = (
    STATEMENT_VARDECL_SCHEMA, statement_vardecl_of_json
)

# --------------------------------------------------------------------
STATEMENT_VARDECL_SCHEMA = [
    ('lvalue', 'lvalue'    ),
    ('rvalue', 'expression'),
]

def statement_assign_of_json(data):
    return AssignStatement(
        lhs = parse_name(data['lvalue'][1]['name']),
        rhs = expression_of_json(*data['rvalue']),
    )

JSON_STATEMENTS['assign'] = (
    STATEMENT_VARDECL_SCHEMA, statement_assign_of_json
)

# --------------------------------------------------------------------
STATEMENT_EVAL_SCHEMA = [
    ('expression', 'expression'),
]

def statement_eval_of_json(data):
    expression = data['expression']

    try:
        if expression[0] != '<expression:call>':
            raise InvalidBXJSon

        if parse_name(expression[1]['target']) != 'print':
            raise InvalidBXJSon

    except IndexError:
        raise InvalidBXJSon

    return PrintStatement(
        value = expression_of_json(*expression[1]['arguments'][0]),
    )

JSON_STATEMENTS['eval'] = (
    STATEMENT_EVAL_SCHEMA, statement_eval_of_json
)

# --------------------------------------------------------------------
def bxprogram_of_json(data):
    try:
        body = data['ast'][0][1]['body']
    except IndexError:
        raise InvalidBXJSon

    return list(statement_of_json(*x) for x in body)

# --------------------------------------------------------------------
def _main():
    if len(sys.argv)-1 != 1:
        print(f'Usage: {os.path.basename(sys.argv[0])} [INPUT]')
        exit(1)

    with open(sys.argv[1], 'r') as stream:
        data = json.load(stream)

    prgm = bxprogram_of_json(data)

    print(prgm)

# --------------------------------------------------------------------
if __name__ == '__main__':
    _main()
