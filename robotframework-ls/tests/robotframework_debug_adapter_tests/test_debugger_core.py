import pytest
import os


class DummyBusyWait(object):
    def __init__(self, debugger_impl):
        self.debugger_impl = debugger_impl
        self.waited = 0
        self.proceeded = 0
        self.stack = []
        self.on_wait = []

    def wait(self):
        from robotframework_debug_adapter.constants import MAIN_THREAD_ID

        self.waited += 1
        self.stack.append(self.debugger_impl._get_stack_info(MAIN_THREAD_ID))
        action = self.on_wait.pop(0)
        action()

    def proceed(self):
        self.proceeded += 1


@pytest.fixture
def run_robot_cli(dap_logs_dir):
    def run(target):
        import robot

        code = robot.run_cli(
            [
                "--outputdir=%s" % (dap_logs_dir,),
                "--listener=robotframework_debug_adapter.listeners.DebugListener",
                target,
            ],
            exit=False,
        )
        return code

    yield run


def test_debugger_core(debugger_api, run_robot_cli):
    from robotframework_debug_adapter.debugger_impl import patch_execution_context
    from robotframework_debug_adapter.debugger_impl import RobotBreakpoint

    debugger_impl = patch_execution_context()
    target = debugger_api.get_dap_case_file("case_log.robot")
    debugger_api.target = target
    line = debugger_api.get_line_index_with_content("check that log works")
    debugger_impl.set_breakpoints(target, RobotBreakpoint(line))

    busy_wait = DummyBusyWait(debugger_impl)
    debugger_impl.busy_wait = busy_wait
    busy_wait.on_wait = [debugger_impl.step_continue]

    code = run_robot_cli(target)
    assert busy_wait.waited == 1
    assert busy_wait.proceeded == 1
    assert len(busy_wait.stack) == 1
    assert code == 0


def stack_frames_repr(busy_wait):
    dct = {}

    def to_dict(stack_frame):
        dct = stack_frame.to_dict()
        del dct["id"]
        path = dct["source"]["path"]
        if path != "None":
            assert os.path.exists(path)
            # i.e.: make the path machine-independent
            dct["source"]["path"] = ".../" + os.path.basename(path)
        return dct

    for i, stack_lst in enumerate(busy_wait.stack):
        dct["Stack %s" % (i,)] = [to_dict(x) for x in stack_lst.dap_frames]
    return dct


def test_debugger_core_for(debugger_api, run_robot_cli, data_regression):
    from robotframework_debug_adapter.debugger_impl import patch_execution_context
    from robotframework_debug_adapter.debugger_impl import RobotBreakpoint

    debugger_impl = patch_execution_context()
    target = debugger_api.get_dap_case_file(
        "case_control_flow/case_control_flow_for.robot"
    )
    line = debugger_api.get_line_index_with_content("Break 1", target)
    debugger_impl.set_breakpoints(target, RobotBreakpoint(line))

    busy_wait = DummyBusyWait(debugger_impl)
    debugger_impl.busy_wait = busy_wait
    busy_wait.on_wait = [
        debugger_impl.step_in,
        debugger_impl.step_in,
        debugger_impl.step_in,
        debugger_impl.step_continue,
    ]

    code = run_robot_cli(target)

    assert busy_wait.waited == 4
    assert busy_wait.proceeded == 4
    assert len(busy_wait.stack) == 4

    data_regression.check(stack_frames_repr(busy_wait))
    assert code == 0


def test_debugger_core_keyword_if(debugger_api, run_robot_cli, data_regression):
    from robotframework_debug_adapter.debugger_impl import patch_execution_context
    from robotframework_debug_adapter.debugger_impl import RobotBreakpoint

    debugger_impl = patch_execution_context()
    target = debugger_api.get_dap_case_file(
        "case_control_flow/case_control_flow_for.robot"
    )
    line = debugger_api.get_line_index_with_content("Break 2", target)
    debugger_impl.set_breakpoints(target, RobotBreakpoint(line))

    busy_wait = DummyBusyWait(debugger_impl)
    debugger_impl.busy_wait = busy_wait
    busy_wait.on_wait = [
        debugger_impl.step_in,
        debugger_impl.step_in,
        debugger_impl.step_in,
        debugger_impl.step_continue,
    ]

    code = run_robot_cli(target)

    assert busy_wait.waited == 4
    assert busy_wait.proceeded == 4
    assert len(busy_wait.stack) == 4

    data_regression.check(stack_frames_repr(busy_wait))
    assert code == 0


def test_debugger_core_step_in(debugger_api, run_robot_cli):
    from robotframework_debug_adapter.debugger_impl import patch_execution_context
    from robotframework_debug_adapter.debugger_impl import RobotBreakpoint

    debugger_impl = patch_execution_context()
    target = debugger_api.get_dap_case_file("case4/case4.robot")
    line = debugger_api.get_line_index_with_content(
        "My Equal Redefined   2   2", target
    )
    debugger_impl.set_breakpoints(target, RobotBreakpoint(line))

    busy_wait = DummyBusyWait(debugger_impl)
    debugger_impl.busy_wait = busy_wait
    busy_wait.on_wait = [debugger_impl.step_in, debugger_impl.step_continue]

    code = run_robot_cli(target)

    assert busy_wait.waited == 2
    assert busy_wait.proceeded == 2
    assert len(busy_wait.stack) == 2
    assert [x.name for x in busy_wait.stack[0].dap_frames] == [
        "My Equal Redefined",
        "TestCase: Can use resource keywords",
        "TestSuite: Case4",
    ]
    assert [x.name for x in busy_wait.stack[1].dap_frames] == [
        "Should Be Equal",
        "My Equal Redefined",
        "TestCase: Can use resource keywords",
        "TestSuite: Case4",
    ]
    assert code == 0


def test_debugger_core_step_next(debugger_api, run_robot_cli):
    from robotframework_debug_adapter.debugger_impl import patch_execution_context
    from robotframework_debug_adapter.debugger_impl import RobotBreakpoint

    debugger_impl = patch_execution_context()
    target = debugger_api.get_dap_case_file("case4/case4.robot")
    line = debugger_api.get_line_index_with_content(
        "My Equal Redefined   2   2", target
    )
    debugger_impl.set_breakpoints(target, RobotBreakpoint(line))

    busy_wait = DummyBusyWait(debugger_impl)
    debugger_impl.busy_wait = busy_wait
    busy_wait.on_wait = [debugger_impl.step_next, debugger_impl.step_continue]

    code = run_robot_cli(target)

    assert busy_wait.waited == 2
    assert busy_wait.proceeded == 2
    assert len(busy_wait.stack) == 2
    assert [x.name for x in busy_wait.stack[0].dap_frames] == [
        "My Equal Redefined",
        "TestCase: Can use resource keywords",
        "TestSuite: Case4",
    ]
    assert [x.name for x in busy_wait.stack[1].dap_frames] == [
        "Yet Another Equal Redefined",
        "TestCase: Can use resource keywords",
        "TestSuite: Case4",
    ]
    assert code == 0


def test_debugger_core_step_out(debugger_api, run_robot_cli):
    from robotframework_debug_adapter.debugger_impl import patch_execution_context
    from robotframework_debug_adapter.debugger_impl import RobotBreakpoint

    debugger_impl = patch_execution_context()
    target = debugger_api.get_dap_case_file("case_step_out.robot")
    line = debugger_api.get_line_index_with_content("Break 1", target)
    debugger_impl.set_breakpoints(target, RobotBreakpoint(line))

    busy_wait = DummyBusyWait(debugger_impl)
    debugger_impl.busy_wait = busy_wait
    busy_wait.on_wait = [debugger_impl.step_out, debugger_impl.step_continue]

    code = run_robot_cli(target)

    assert busy_wait.waited == 2
    assert busy_wait.proceeded == 2
    assert len(busy_wait.stack) == 2
    assert [x.name for x in busy_wait.stack[0].dap_frames] == [
        "Should Be Equal",
        "My Equal Redefined",
        "TestCase: Can use resource keywords",
        "TestSuite: Case Step Out",
    ]
    assert [x.name for x in busy_wait.stack[1].dap_frames] == [
        "Yet Another Equal Redefined",
        "TestCase: Can use resource keywords",
        "TestSuite: Case Step Out",
    ]
    assert code == 0


def test_debugger_core_with_setup_teardown(
    debugger_api, run_robot_cli, data_regression
):
    from robotframework_debug_adapter.debugger_impl import patch_execution_context
    from robotframework_debug_adapter.debugger_impl import RobotBreakpoint

    debugger_impl = patch_execution_context()
    target = debugger_api.get_dap_case_file("case_setup_teardown.robot")
    debugger_impl.set_breakpoints(
        target,
        (
            RobotBreakpoint(
                debugger_api.get_line_index_with_content("Suite Setup", target)
            ),
            RobotBreakpoint(
                debugger_api.get_line_index_with_content("Suite Teardown", target)
            ),
        ),
    )

    busy_wait = DummyBusyWait(debugger_impl)
    debugger_impl.busy_wait = busy_wait
    busy_wait.on_wait = [debugger_impl.step_continue, debugger_impl.step_continue]

    code = run_robot_cli(target)

    assert busy_wait.waited == 2
    assert busy_wait.proceeded == 2
    assert len(busy_wait.stack) == 2

    data_regression.check(stack_frames_repr(busy_wait))

    assert code == 0
