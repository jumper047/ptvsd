# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See LICENSE in the project root
# for license information.

from __future__ import print_function, with_statement, absolute_import

from pytests.helpers import print
from pytests.helpers.pattern import ANY
from pytests.helpers.timeline import Event


def test_variables_and_evaluate(debug_session, pyfile, run_as, start_method):

    @pyfile
    def code_to_debug():
        from dbgimporter import import_and_enable_debugger
        import_and_enable_debugger()
        a = 1
        b = {"one": 1, "two": 2}
        c = 3
        print([a, b, c])

    bp_line = 6
    bp_file = code_to_debug
    debug_session.initialize(target=(run_as, bp_file), start_method=start_method)
    debug_session.set_breakpoints(bp_file, [bp_line])
    debug_session.start_debugging()
    hit = debug_session.wait_for_thread_stopped()

    resp_scopes = debug_session.send_request('scopes', arguments={
        'frameId': hit.frame_id,
    }).wait_for_response()
    scopes = resp_scopes.body['scopes']
    assert len(scopes) > 0

    resp_variables = debug_session.send_request('variables', arguments={
        'variablesReference': scopes[0]['variablesReference']
    }).wait_for_response()
    variables = list(v for v in resp_variables.body['variables'] if v['name'] in ['a', 'b', 'c'])
    assert len(variables) == 3

    # variables should be sorted alphabetically
    assert ['a', 'b', 'c'] == list(v['name'] for v in variables)

    # get contents of 'b'
    resp_b_variables = debug_session.send_request('variables', arguments={
        'variablesReference': variables[1]['variablesReference']
    }).wait_for_response()
    b_variables = resp_b_variables.body['variables']
    assert len(b_variables) == 3
    assert b_variables[0] == {
        'type': 'int',
        'value': '1',
        'name': ANY.such_that(lambda x: x.find('one') > 0),
        'evaluateName': "b['one']"
    }
    assert b_variables[1] == {
        'type': 'int',
        'value': '2',
        'name': ANY.such_that(lambda x: x.find('two') > 0),
        'evaluateName': "b['two']"
    }
    assert b_variables[2] == {
        'type': 'int',
        'value': '2',
        'name': '__len__',
        'evaluateName': "b.__len__"
    }

    # simple variable
    resp_evaluate1 = debug_session.send_request('evaluate', arguments={
        'expression': 'a', 'frameId': hit.frame_id,
    }).wait_for_response()
    assert resp_evaluate1.body == ANY.dict_with({
        'type': 'int',
        'result': '1'
    })

    # dict variable
    resp_evaluate2 = debug_session.send_request('evaluate', arguments={
        'expression': 'b["one"]', 'frameId': hit.frame_id,
    }).wait_for_response()
    assert resp_evaluate2.body == ANY.dict_with({
        'type': 'int',
        'result': '1'
    })

    # expression evaluate
    resp_evaluate3 = debug_session.send_request('evaluate', arguments={
        'expression': 'a + b["one"]', 'frameId': hit.frame_id,
    }).wait_for_response()
    assert resp_evaluate3.body == ANY.dict_with({
        'type': 'int',
        'result': '2'
    })

    debug_session.send_request('continue').wait_for_response()
    debug_session.wait_for_next(Event('continued'))

    debug_session.wait_for_exit()


def test_set_variable(debug_session, pyfile, run_as, start_method):
    @pyfile
    def code_to_debug():
        from dbgimporter import import_and_enable_debugger
        import_and_enable_debugger()
        a = 1
        print(a)

    bp_line = 4
    bp_file = code_to_debug
    debug_session.initialize(target=(run_as, bp_file), start_method=start_method)
    debug_session.set_breakpoints(bp_file, [bp_line])
    debug_session.start_debugging()
    hit = debug_session.wait_for_thread_stopped()

    resp_scopes = debug_session.send_request('scopes', arguments={
        'frameId': hit.frame_id
    }).wait_for_response()
    scopes = resp_scopes.body['scopes']
    assert len(scopes) > 0

    resp_variables = debug_session.send_request('variables', arguments={
        'variablesReference': scopes[0]['variablesReference']
    }).wait_for_response()
    variables = list(v for v in resp_variables.body['variables'] if v['name'] == 'a')
    assert len(variables) == 1
    assert variables[0] == {
        'type': 'int',
        'value': '1',
        'name': 'a',
        'evaluateName': "a"
    }

    resp_set_variable = debug_session.send_request('setVariable', arguments={
        'variablesReference': scopes[0]['variablesReference'],
        'name': 'a',
        'value': '1000'
    }).wait_for_response()
    assert resp_set_variable.body == ANY.dict_with({
        'type': 'int',
        'value': '1000'
    })

    debug_session.send_request('continue').wait_for_response()
    debug_session.wait_for_next(Event('continued'))

    debug_session.wait_for_next(Event('output'))
    output = [e for e in debug_session.all_occurrences_of(Event('output'))
              if e.body['output'].startswith('1000')]
    assert any(output)

    debug_session.wait_for_exit()


def test_variable_sort(debug_session, pyfile, run_as, start_method):

    @pyfile
    def code_to_debug():
        from dbgimporter import import_and_enable_debugger
        import_and_enable_debugger()
        b_test = {"spam": "A", "eggs": "B", "abcd": "C"}  # noqa
        _b_test = 12  # noqa
        __b_test = 13  # noqa
        __b_test__ = 14  # noqa
        a_test = 1  # noqa
        _a_test = 2  # noqa
        __a_test = 3  # noqa
        __a_test__ = 4  # noqa
        c_test = {1: "one", 2: "two", 10: "ten"}  # noqa
        _c_test = 22  # noqa
        __c_test = 23  # noqa
        __c_test__ = 24  # noqa
        d = 3  # noqa
        print('done')

    bp_line = 15
    bp_file = code_to_debug
    debug_session.initialize(target=(run_as, bp_file), start_method=start_method)
    debug_session.set_breakpoints(bp_file, [bp_line])
    debug_session.start_debugging()
    hit = debug_session.wait_for_thread_stopped()

    resp_scopes = debug_session.send_request('scopes', arguments={
        'frameId': hit.frame_id
    }).wait_for_response()
    scopes = resp_scopes.body['scopes']
    assert len(scopes) > 0

    resp_variables = debug_session.send_request('variables', arguments={
        'variablesReference': scopes[0]['variablesReference']
    }).wait_for_response()
    variable_names = list(v['name'] for v in resp_variables.body['variables']
                          if v['name'].find('_test') > 0)
    assert variable_names == [
            'a_test', 'b_test', 'c_test', '_a_test', '_b_test', '_c_test',
            '__a_test', '__b_test', '__c_test', '__a_test__', '__b_test__',
            '__c_test__'
        ]

    # ensure string dict keys are sorted
    b_test_variable = list(v for v in resp_variables.body['variables'] if v['name'] == 'b_test')
    assert len(b_test_variable) == 1
    resp_dict_variables = debug_session.send_request('variables', arguments={
        'variablesReference': b_test_variable[0]['variablesReference']
    }).wait_for_response()
    variable_names = list(v['name'][1:5] for v in resp_dict_variables.body['variables'])
    assert len(variable_names) == 4
    assert variable_names[:3] == ['abcd', 'eggs', 'spam']

    # ensure numeric dict keys are sorted
    c_test_variable = list(v for v in resp_variables.body['variables'] if v['name'] == 'c_test')
    assert len(c_test_variable) == 1
    resp_dict_variables2 = debug_session.send_request('variables', arguments={
        'variablesReference': c_test_variable[0]['variablesReference']
    }).wait_for_response()
    variable_names = list(v['name'] for v in resp_dict_variables2.body['variables'])
    assert len(variable_names) == 4
    # NOTE: this is commented out due to sorting bug #213
    # assert variable_names[:3] == ['1', '2', '10']

    debug_session.send_request('continue').wait_for_response()
    debug_session.wait_for_next(Event('continued'))

    debug_session.wait_for_exit()
