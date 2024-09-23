import sys
import re
import copy

class InterpreterError(Exception):
    """Custom exception class for Interpreter errors."""
    pass

class FunctionReturn(Exception):
    """Custom exception to handle return statements within functions."""
    def __init__(self, value):
        self.value = value

class Variable:
    """
    Đại diện cho một biến với kiểu dữ liệu, tên và giá trị.
    """
    def __init__(self, var_type, name, value=None):
        self.type = var_type.lower()
        self.name = name
        self.value = value

    def __repr__(self):
        return f"{self.type} {self.name} = {self.value}"


class Function:
    """
    Đại diện cho một hàm với tên, tham số đầu vào, mã lệnh và nguồn dữ liệu.
    """
    def __init__(self, name, parameters, code, source="direct"):
        self.name = name
        self.parameters = parameters  # Danh sách các tham số đầu vào
        self.code = code  # Danh sách các dòng mã lệnh
        self.source = source  # Nguồn dữ liệu của hàm, mặc định là 'direct'

    def __repr__(self):
        return (f"Function(name={self.name}, parameters={self.parameters}, source={self.source})")

class ClassDefinition:
    def __init__(self, name, inputs, outputs, code, functions=None, lib_code=None):
        self.name = name
        self.inputs = inputs  # List of (type, name)
        self.outputs = outputs  # List of (type, name)
        self.code = code  # List of code lines in ENV CAL
        self.functions = functions or {}  # Dict of functions defined in the class
        self.lib_code = lib_code or []  # List of code lines in LIB section
        self.is_interacting = False  # Cờ để kiểm tra nếu có tương tác

    def start_interaction(self):
        """Kích hoạt giao tiếp."""
        self.is_interacting = True

    def stop_interaction(self):
        """Dừng giao tiếp."""
        self.is_interacting = False

    def __repr__(self):
        interaction_msg = " [Interacting...]" if self.is_interacting else ""
        return (f"ClassDefinition(name={self.name}, inputs={self.inputs}, "
                f"outputs={self.outputs}, functions={list(self.functions.keys())}, "
                f"lib_code={self.lib_code}){interaction_msg}")


class Interpreter:
    """
    Trình thông dịch cho ngôn ngữ kịch bản tùy chỉnh với hỗ trợ hàm và cấu trúc lớp.
    """
    def __init__(self):
        self.global_variables = {}      # Biến toàn cục
        self.variables = [self.global_variables]  # Ngăn xếp phạm vi biến
        self.functions = {}             # Lưu trữ định nghĩa hàm
        self.classes = {}               # Lưu trữ định nghĩa lớp
        self.command_patterns = {
            'VAR': re.compile(
                r'^VAR\s+--type\s+(?P<type>\w+)\s+--name\s+(?P<name>\w+)(?:\s+--set\s+(?P<set>.+))?$'
            ),
            'SUM': re.compile(
                r'^SUM(?:\s+--input\s+(?P<input>\w+))+\s+--output\s+(?P<output>\w+)$'
            ),
            'SUBTRACT': re.compile(
                r'^SUBTRACT(?:\s+--input\s+(?P<input>\w+))+\s+--output\s+(?P<output>\w+)$'
            ),
            'MULTIPLY': re.compile(
                r'^MULTIPLY(?:\s+--input\s+(?P<input>\w+))+\s+--output\s+(?P<output>\w+)$'
            ),
            'DIVIDE': re.compile(
                r'^DIVIDE(?:\s+--input\s+(?P<input>\w+))+\s+--output\s+(?P<output>\w+)$'
            ),
            'FOR': re.compile(
                r'^FOR(?:\s+--var\s+(?P<var>\w+))?\s+--start\s+(?P<start>\w+)\s+--end\s+(?P<end>\w+)\s+--step\s+(?P<step>\w+)$'
            ),
            'IF': re.compile(
                r'^IF\s+(?P<condition>.+)$'
            ),
            'ELSE': re.compile(
                r'^ELSE$'
            ),
            'WHILE': re.compile(
                r'^WHILE\s+(?P<condition>.+)$'
            ),
            'END': re.compile(
                r'^END$'
            ),
            'MEM_RELEASE': re.compile(
                r'^MEM\s+--release\s+(?P<name>\w+)$'
            ),
            'PRI_PRINT': re.compile(
                r'^PRI\s+--print\s+(?P<var>\w+)$'
            ),
            'DEF_CREATE': re.compile(
                r'^DEF\s+--create\s+(?P<name_def>\w+)(?:\s+--input\s+(?P<inputs>\w+))*\s*$'
            ),
            'DEF_CALL': re.compile(
                r'^DEF\s+--call\s+(?P<name_def>\w+)(?:\s+--input\s+(?P<inputs>\w+))*\s+--save\s+(?P<save>\w+)$'
            ),
            'RETURN': re.compile(
                r'^RETURN\s+(?P<var>\w+)$'
            ),
            'FILE_READ': re.compile(
                r'^FILE\s+--read\s+(?P<path>\S+)\s+--save\s+(?P<save>\w+)$'
            ),
            'FILE_SAVE': re.compile(
                r'^FILE\s+--save\s+(?P<data>\w+)\s+--to\s+(?P<path>\S+)$'
            ),
            'IMP': re.compile(
                r'^IMP\s+--from\s+(?P<path>\S+)\s+--import\s+(?P<name_def>\w+)$'
            ),
            'ARR_CREATE': re.compile(
                r'^ARR\s+--array\s+--create\s+(?P<name>\w+)\s+--max\s+(?P<max>\d+)$'
            ),
            'ARR_SET_DATA': re.compile(
                r'^ARR\s+--array\s+--name\s+(?P<name>\w+)\s+--set_data\s+(?P<variable>\w+)\s+--pos\s+(?P<pos>\d+)$'
            ),
            'ARR_GET_DATA': re.compile(
                r'^ARR\s+--array\s+--name\s+(?P<name>\w+)\s+--get_data\s+(?P<index>\d+)\s+--save\s+(?P<save>\w+)$'
            ),
            'LOAD': re.compile(
                r'^LOAD\s+--from\s+(?P<path>\S+)(?:\s+--input\s+(?P<inputs>\w+))*\s*(?:\s+--save\s+(?P<saves>\w+))*\s*$'
            ),
        }
    
    # Các phương thức liên quan đến mảng
    def execute_array_create(self, args):
        # Nội dung như trước
        name = args.get('name')
        max_size = int(args.get('max'))

        if not name or max_size <= 0:
            raise InterpreterError("Lỗi: Lệnh ARR --create cần một tên và số phần tử lớn hơn 0")

        # Tạo mảng dưới dạng danh sách với kích thước xác định
        array = [0] * max_size
        var = Variable('array', name, array)
        self.set_variable(var)
        print(f"Đã tạo mảng '{name}' với kích thước {max_size}")

    def execute_array_set_data(self, args):
        # Nội dung như trước
        name = args.get('name')
        variable_name = args.get('variable')
        pos = int(args.get('pos'))

        # Kiểm tra mảng có tồn tại không
        array_var = self.get_variable(name)
        if array_var is None or array_var.type != 'array':
            raise InterpreterError(f"Lỗi: Mảng '{name}' không tồn tại")

        # Kiểm tra vị trí có hợp lệ không
        if pos < 0 or pos >= len(array_var.value):
            raise InterpreterError(f"Lỗi: Vị trí {pos} nằm ngoài phạm vi của mảng '{name}'")

        # Lấy giá trị của biến
        data_var = self.get_variable(variable_name)
        if data_var is None:
            raise InterpreterError(f"Lỗi: Biến '{variable_name}' không tồn tại")

        # Gán giá trị vào mảng
        array_var.value[pos] = data_var.value
        print(f"Đã gán giá trị '{data_var.value}' vào vị trí {pos} của mảng '{name}'")
        
    def execute_array_get_data(self, args):
        # Nội dung như trước
        name = args.get('name')
        index = int(args.get('index'))
        save_var_name = args.get('save')

        # Kiểm tra mảng có tồn tại không
        array_var = self.get_variable(name)
        if array_var is None or array_var.type != 'array':
            raise InterpreterError(f"Lỗi: Mảng '{name}' không tồn tại")

        # Kiểm tra vị trí có hợp lệ không
        if index < 0 or index >= len(array_var.value):
            raise InterpreterError(f"Lỗi: Vị trí {index} nằm ngoài phạm vi của mảng '{name}'")

        # Lấy giá trị từ mảng
        data = array_var.value[index]
        if data is None:
            raise InterpreterError(f"Lỗi: Mảng '{name}' tại vị trí {index} không có giá trị")

        # Lưu giá trị vào biến mới
        save_var = Variable('auto', save_var_name, data)
        self.set_variable(save_var)
        print(f"Đã lấy giá trị '{data}' từ vị trí {index} của mảng '{name}' và lưu vào '{save_var_name}'")

    # Các phương thức khác
    def execute_imp(self, args, local_functions=None):
        path = args.get('path')
        name_def = args.get('name_def')

        if not path or not name_def:
            raise InterpreterError("Error: IMP command requires --from and --import arguments")

        # Read content from file
        try:
            with open(path, 'r', encoding="utf8") as file:
                file_content = file.read()
        except FileNotFoundError:
            raise InterpreterError(f"Error: File '{path}' not found")
        except IOError:
            raise InterpreterError(f"Error: Cannot read file '{path}'")

        # Execute the content of the file to load functions into memory
        self.interpret(file_content, local_functions=local_functions)

        # Check if the function has been added to the functions dictionary
        functions_dict = local_functions if local_functions is not None else self.functions

        if name_def not in functions_dict:
            raise InterpreterError(f"Error: Function '{name_def}' not found in file '{path}'")

        print(f"Function '{name_def}' has been imported from file '{path}'")


    def execute_file_read(self, args):
        # Nội dung như trước
        path = args.get('path')
        save_var_name = args.get('save')

        if not path or not save_var_name:
            raise InterpreterError("Lỗi: Lệnh FILE --read cần một đường dẫn tập tin và một biến để lưu dữ liệu")

        # Đọc nội dung từ file
        try:
            with open(path, 'r') as file:
                data = file.read()
        except FileNotFoundError:
            raise InterpreterError(f"Lỗi: Tập tin '{path}' không tìm thấy")
        except IOError:
            raise InterpreterError(f"Lỗi: Không thể đọc tập tin '{path}'")

        # Lưu nội dung vào biến (dưới dạng chuỗi)
        var = Variable('str', save_var_name, data)
        self.set_variable(var)
        print(f"Đã đọc dữ liệu từ '{path}' và lưu vào biến '{save_var_name}'")

    def execute_file_save(self, args):
        # Nội dung như trước
        data_var_name = args.get('data')
        path = args.get('path')

        if not data_var_name or not path:
            raise InterpreterError("Lỗi: Lệnh FILE --save cần một tên biến và một đường dẫn tập tin")

        # Lấy dữ liệu từ biến
        var = self.get_variable(data_var_name)
        if var is None:
            raise InterpreterError(f"Lỗi: Biến '{data_var_name}' không tồn tại")

        if var.type != 'str':
            raise InterpreterError(f"Lỗi: Biến '{data_var_name}' phải là chuỗi để ghi vào tập tin")

        # Ghi dữ liệu vào file
        try:
            with open(path, 'w') as file:
                file.write(var.value)
        except IOError:
            raise InterpreterError(f"Lỗi: Không thể ghi vào tập tin '{path}'")

        print(f"Đã lưu dữ liệu từ biến '{data_var_name}' vào tập tin '{path}'")

    def execute_print(self, args):
        # Nội dung như trước
        var_name = args.get('var')

        # Kiểm tra xem biến có tồn tại hay không
        var = self.get_variable(var_name)
        if var is None:
            raise InterpreterError(f"Lỗi: Biến '{var_name}' không tồn tại.")

        # In giá trị của biến ra màn hình
        print(f"{var.name}: {var.value}")

    def parse_line(self, line):
        """
        Phân tích một dòng lệnh và trích xuất lệnh cùng các tham số sử dụng regex.
        """
        # Loại bỏ chú thích và khoảng trắng
        line = line.split('#')[0].strip()
        if not line:
            return None, {}

        for command, pattern in self.command_patterns.items():
            match = pattern.match(line)
            if match:
                args = match.groupdict()
                # Xử lý nhiều tham số --input
                if 'input' in args and args['input'] is not None:
                    inputs = re.findall(r'--input\s+(\w+)', line)
                    args['input'] = inputs
                elif 'inputs' in args and args['inputs'] is not None:
                    inputs = re.findall(r'--input\s+(\w+)', line)
                    args['inputs'] = inputs
                if 'saves' in args and args['saves'] is not None:
                    saves = re.findall(r'--save\s+(\w+)', line)
                    args['saves'] = saves
                return command.upper(), args

        raise InterpreterError(f"Error: Unable to parse line: '{line}'")

    def get_variable(self, name, scopes=None):
        """
        Lấy biến từ phạm vi hiện tại hoặc phạm vi được cung cấp.
        Phạm vi hiện tại (cục bộ) được ưu tiên.
        """
        scopes = scopes or self.variables
        for scope in reversed(scopes):
            if name in scope:
                return scope[name]
        return None

    def set_variable(self, var):
        """
        Đặt biến vào phạm vi hiện tại.
        """
        self.variables[-1][var.name] = var

    def execute_var(self, args):
        # Nội dung như trước
        var_type = args.get('type')
        name = args.get('name')
        value = args.get('set')

        if not all([var_type, name]):
            raise InterpreterError("Error: VAR command requires --type and --name")

        # Chuyển đổi kiểu dữ liệu
        try:
            if var_type.lower() == 'int':
                value = int(value) if value is not None else 0
            elif var_type.lower() == 'float':
                value = float(value) if value is not None else 0.0
            elif var_type.lower() == 'str':
                value = str(value) if value is not None else ""
            else:
                raise InterpreterError(f"Error: Unsupported type '{var_type}'")
        except ValueError:
            raise InterpreterError(f"Error: Invalid value for type '{var_type}'")

        var = Variable(var_type, name, value)
        self.set_variable(var)
        print(f"Declared variable: {var}")

    def execute_mem_release(self, args):
        # Nội dung như trước
        var_name = args.get('name')
        if not var_name:
            raise InterpreterError("Error: MEM --release requires a variable name")

        # Tìm kiếm và xóa biến trong phạm vi hiện tại hoặc toàn cục
        for scope in reversed(self.variables):
            if var_name in scope:
                del scope[var_name]
                print(f"Released variable '{var_name}' from memory")
                return

        # Nếu không tìm thấy biến
        raise InterpreterError(f"Error: Variable '{var_name}' not found")

    def execute_sum(self, args):
        # Nội dung như trước
        inputs = args.get('input', [])
        output = args.get('output')

        if not inputs or not output:
            raise InterpreterError("Error: SUM command requires --input(s) and --output")

        if len(inputs) < 2:
            raise InterpreterError("Error: SUM command requires at least two --input arguments")

        total = 0
        for var_name in inputs:
            var = self.get_variable(var_name)
            total += self._get_numeric_value(var, var_name, 'SUM')

        self._assign_output(output, total, 'SUM')

    def execute_subtract(self, args):
        # Nội dung như trước
        inputs = args.get('input', [])
        output = args.get('output')

        if not inputs or not output:
            raise InterpreterError("Error: SUBTRACT command requires --input(s) and --output")

        if len(inputs) < 2:
            raise InterpreterError("Error: SUBTRACT command requires at least two --input arguments")

        var = self.get_variable(inputs[0])
        result = self._get_numeric_value(var, inputs[0], 'SUBTRACT')

        for var_name in inputs[1:]:
            var = self.get_variable(var_name)
            value = self._get_numeric_value(var, var_name, 'SUBTRACT')
            result -= value

        self._assign_output(output, result, 'SUBTRACT')

    def execute_multiply(self, args):
        # Nội dung như trước
        inputs = args.get('input', [])
        output = args.get('output')

        if not inputs or not output:
            raise InterpreterError("Error: MULTIPLY command requires --input(s) and --output")

        if len(inputs) < 2:
            raise InterpreterError("Error: MULTIPLY command requires at least two --input arguments")

        result = 1
        for var_name in inputs:
            var = self.get_variable(var_name)
            value = self._get_numeric_value(var, var_name, 'MULTIPLY')
            result *= value

        self._assign_output(output, result, 'MULTIPLY')

    def execute_divide(self, args):
        # Nội dung như trước
        inputs = args.get('input', [])
        output = args.get('output')

        if not inputs or not output:
            raise InterpreterError("Error: DIVIDE command requires --input(s) and --output")

        if len(inputs) < 2:
            raise InterpreterError("Error: DIVIDE command requires at least two --input arguments")

        var = self.get_variable(inputs[0])
        result = self._get_numeric_value(var, inputs[0], 'DIVIDE')

        for var_name in inputs[1:]:
            var = self.get_variable(var_name)
            value = self._get_numeric_value(var, var_name, 'DIVIDE')
            if value == 0:
                raise InterpreterError("Error: Division by zero")
            result /= value

        self._assign_output(output, result, 'DIVIDE')

    def execute_def_create(self, args, code_lines, local_functions=None):
        name_def = args.get('name_def')
        inputs = args.get('inputs', [])
        parameters = inputs if inputs else []

        function = Function(name_def, parameters, code_lines, source="direct")

        if local_functions is not None:
            local_functions[name_def] = function
        else:
            self.functions[name_def] = function

        print(f"Đã định nghĩa hàm: {function}")


    def execute_def_call(self, args, local_functions=None, class_scope=None):
        name_def = args.get('name_def')
        inputs = args.get('inputs', [])
        save_var = args.get('save')

        # Tìm kiếm hàm trong phạm vi cục bộ trước
        if local_functions and name_def in local_functions:
            function = local_functions[name_def]
        elif name_def in self.functions:
            function = self.functions[name_def]
        else:
            raise InterpreterError(f"Error: Function '{name_def}' is not defined")

        if len(inputs) != len(function.parameters):
            raise InterpreterError(f"Error: Function '{name_def}' expects {len(function.parameters)} arguments, got {len(inputs)}")

        # Tạo một ngăn xếp mới cho các biến cục bộ của hàm
        local_scope = {}
        for param, input_var in zip(function.parameters, inputs):
            var = self.get_variable(input_var, scopes=self.variables + [class_scope] if class_scope else self.variables)
            if var is None:
                raise InterpreterError(f"Error: Variable '{input_var}' not defined for function parameter '{param}'")
            # Tạo một bản sao của biến để không ảnh hưởng đến biến gốc
            local_scope[param] = Variable(var.type, param, var.value)

        # Thêm phạm vi cục bộ vào ngăn xếp biến
        self.variables.append(local_scope)

        try:
            # Thực thi mã lệnh của hàm
            self.interpret('\n'.join(function.code), in_function=True, local_functions=local_functions, class_scope=class_scope)
        except FunctionReturn as fr:
            # Nhận giá trị trả về từ hàm
            return_value = fr.value
        finally:
            # Loại bỏ phạm vi cục bộ
            self.variables.pop()

        # Gán giá trị trả về vào biến lưu
        if save_var:
            output_var = self.get_variable(save_var)
            if not output_var:
                # Nếu biến chưa tồn tại, tạo biến mới
                output_var = Variable('auto', save_var, return_value)
                self.set_variable(output_var)
            else:
                if output_var.type not in ['int', 'float', 'str', 'auto']:
                    raise InterpreterError(f"Error: Unsupported type '{output_var.type}' for saving function return value")

                # Chuyển đổi kiểu dữ liệu dựa trên loại biến lưu
                try:
                    if output_var.type == 'int':
                        return_value = int(return_value)
                    elif output_var.type == 'float':
                        return_value = float(return_value)
                    elif output_var.type == 'str':
                        return_value = str(return_value)
                except ValueError:
                    raise InterpreterError(f"Error: Cannot cast return value to type '{output_var.type}' for variable '{save_var}'")

                output_var.value = return_value
            print(f"Function '{name_def}' returned value {return_value} assigned to '{save_var}'")


    def execute_return(self, args):
        # Nội dung như trước
        var_name = args.get('var')
        var = self.get_variable(var_name)
        if var is None:
            raise InterpreterError(f"Error: Variable '{var_name}' not defined for RETURN")
        # Ném ngoại lệ FunctionReturn với giá trị của biến
        raise FunctionReturn(var.value)

    def _get_numeric_value(self, var, var_name, command_name):
        # Nội dung như trước
        if not var:
            raise InterpreterError(f"Error: Variable '{var_name}' not defined")
        if var.type not in ['int', 'float']:
            raise InterpreterError(f"Error: Variable '{var_name}' is not a number for {command_name} operation")
        return var.value

    def _assign_output(self, output_var_name, value, command_name):
        # Nội dung như trước
        output_var = self.get_variable(output_var_name)
        if not output_var:
            # Nếu biến chưa tồn tại, tạo nó trong phạm vi hiện tại với kiểu số mặc định là int
            output_var = Variable('int', output_var_name, None)
            self.set_variable(output_var)

        if output_var.type not in ['int', 'float']:
            raise InterpreterError(f"Error: Output variable '{output_var_name}' is not a number for {command_name} operation")

        # Chuyển đổi kiểu dữ liệu dựa trên kiểu biến đầu ra
        try:
            if output_var.type == 'int':
                value = int(value)
            elif output_var.type == 'float':
                value = float(value)
        except ValueError:
            raise InterpreterError(f"Error: Cannot cast value to type '{output_var.type}' for variable '{output_var_name}'")

        output_var.value = value
        operation = command_name.capitalize()
        print(f"{operation} result stored in {output_var_name} = {value}")

    def evaluate_condition(self, condition_str):
        # Nội dung như trước
        # Thay thế tên biến bằng giá trị của chúng
        tokens = re.findall(r'\w+|[><=!]=|[><]', condition_str)
        eval_str = ""
        for token in tokens:
            if token in ['>', '<', '>=', '<=', '==', '!=']:
                eval_str += f' {token} '
            else:
                var = self.get_variable(token)
                if var:
                    if var.type in ['int', 'float']:
                        eval_str += str(var.value)
                    elif var.type == 'str':
                        eval_str += f'"{var.value}"'
                    else:
                        raise InterpreterError(f"Error: Unsupported variable type '{var.type}' in condition")
                else:
                    # Giả sử nó là số hoặc chuỗi
                    if re.match(r'^-?\d+(\.\d+)?$', token):
                        eval_str += token
                    else:
                        eval_str += f'"{token}"'
        try:
            # Chỉ cho phép các toán tử logic cơ bản
            allowed_names = {"True": True, "False": False}
            return eval(eval_str, {"__builtins__": None}, allowed_names)
        except Exception:
            raise InterpreterError(f"Error: Invalid condition '{condition_str}'")

    def interpret(self, code, in_function=False, local_functions=None, class_scope=None):
        """
        Xử lý và thực thi toàn bộ kịch bản.
        """
        lines = code.strip().split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line or line.startswith('#'):
                i += 1
                continue

            try:
                command, args = self.parse_line(line)
            except InterpreterError as e:
                raise InterpreterError(f"Line {i+1}: {e}")

            if command in ['FOR', 'IF', 'WHILE', 'DEF_CREATE',]:
                # Xác định khối lệnh bên trong cấu trúc điều khiển
                block_commands = []
                else_commands = []
                i += 1
                nested = 1  # Để xử lý các khối lồng nhau
                while i < len(lines):
                    current_line = lines[i].strip()
                    if not current_line or current_line.startswith('#'):
                        i += 1
                        continue
                    if re.match(self.command_patterns['FOR'], current_line):
                        nested += 1
                    elif re.match(self.command_patterns['IF'], current_line) or re.match(self.command_patterns['WHILE'], current_line) or re.match(self.command_patterns['DEF_CREATE'], current_line):
                        nested += 1
                    elif re.match(self.command_patterns['END'], current_line):
                        nested -= 1
                        if nested == 0:
                            break
                    elif re.match(self.command_patterns['ELSE'], current_line) and nested == 1 and command == 'IF':
                        i += 1
                        while i < len(lines):
                            else_line = lines[i].strip()
                            if not else_line or else_line.startswith('#'):
                                i += 1
                                continue
                            if re.match(self.command_patterns['FOR'], else_line):
                                nested += 1
                            elif re.match(self.command_patterns['IF'], else_line) or re.match(self.command_patterns['WHILE'], else_line) or re.match(self.command_patterns['DEF_CREATE'], else_line):
                                nested += 1
                            elif re.match(self.command_patterns['END'], else_line):
                                nested -= 1
                                if nested == 0:
                                    break
                            else_commands.append(else_line)
                            i += 1
                        break
                    block_commands.append(current_line)
                    i += 1

                # Thực thi cấu trúc điều khiển
                try:
                    if command == 'FOR':
                        self.execute_for(args, block_commands)
                    elif command == 'IF':
                        self.execute_if(args, block_commands, else_commands)
                    elif command == 'WHILE':
                        self.execute_while(args, block_commands)
                    elif command == 'DEF_CREATE':
                        # Xác định mã lệnh của hàm
                        func_code = block_commands
                        self.execute_def_create(args, func_code, local_functions)
                except InterpreterError as e:
                    raise InterpreterError(f"Line {i+1}: {e}")
                except FunctionReturn as fr:
                    if in_function:
                        raise fr  # Cho phép RETURN trả về giá trị từ hàm
                    else:
                        raise InterpreterError("Error: RETURN statement outside of function")
                i += 1  # Bỏ qua 'END'
            elif command == 'RETURN':
                var_name = args.get('var')
                var = self.get_variable(var_name)
                if var is None:
                    raise InterpreterError(f"Error: Variable '{var_name}' not defined for RETURN")
                # Ném ngoại lệ FunctionReturn với giá trị của biến
                raise FunctionReturn(var.value)
            elif command == 'DEF_CALL':
                # Thực thi DEF --call
                self.execute_def_call(args, local_functions, class_scope=class_scope)
                i += 1
            elif command == 'IMP':
                self.execute_imp(args, local_functions=local_functions)
                i += 1
            elif command == 'LOAD':
                self.execute_load(args)
                i += 1
            elif command == 'END':
                # 'END' đã được xử lý trong khi phân tích
                raise InterpreterError("Error: 'END' without matching block")
            else:
                # Thực thi các lệnh đơn
                try:
                    if command == 'VAR':
                        self.execute_var(args)
                    elif command == 'SUM':
                        self.execute_sum(args)
                    elif command == 'SUBTRACT':
                        self.execute_subtract(args)
                    elif command == 'MULTIPLY':
                        self.execute_multiply(args)
                    elif command == 'DIVIDE':
                        self.execute_divide(args)
                    elif command == 'MEM_RELEASE':
                        self.execute_mem_release(args)
                    elif command == 'PRI_PRINT':
                        self.execute_print(args)
                    elif command == 'FILE_READ':
                        self.execute_file_read(args)
                    elif command == 'FILE_SAVE':
                        self.execute_file_save(args)
                    elif command == 'ARR_CREATE':
                        self.execute_array_create(args)
                    elif command == 'ARR_SET_DATA':
                        self.execute_array_set_data(args)
                    elif command == 'ARR_GET_DATA':
                        self.execute_array_get_data(args)
                    else:
                        raise InterpreterError(f"Error: Unknown command '{command}'")
                except InterpreterError as e:
                    raise InterpreterError(f"Line {i+1}: {e}")
                i += 1

    def execute_for(self, args, block_commands):
        # Nội dung như trước
        loop_var = args.get('var') or 'i'  # Biến lặp mặc định là 'i' nếu không chỉ định

        # Lấy giá trị từ biến đã khai báo hoặc giá trị trực tiếp
        start_var = self.get_variable(args.get('start'))
        start = start_var.value if start_var else int(args.get('start'))

        end_var = self.get_variable(args.get('end'))
        end = end_var.value if end_var else int(args.get('end'))

        step_var = self.get_variable(args.get('step'))
        step = step_var.value if step_var else int(args.get('step'))

        # Thêm một phạm vi mới cho vòng lặp
        self.variables.append({})

        # Khởi tạo biến lặp trong phạm vi mới
        loop_variable = Variable('int', loop_var, start)
        self.set_variable(loop_variable)

        # Xác định điều kiện lặp dựa trên bước lặp
        if step > 0:
            condition = lambda x: x <= end
        else:
            condition = lambda x: x >= end

        while condition(self.get_variable(loop_var).value):
            # Thực thi các lệnh trong block_commands
            self.interpret('\n'.join(block_commands), in_function=False)
            # Tăng biến lặp
            self.get_variable(loop_var).value += step

        # Loại bỏ phạm vi của vòng lặp
        self.variables.pop()

    def execute_if(self, args, block_commands, else_commands):
        # Nội dung như trước
        condition_str = args.get('condition')
        condition_result = self.evaluate_condition(condition_str)

        if condition_result:
            # Thêm một phạm vi mới cho khối IF
            self.variables.append({})
            self.interpret('\n'.join(block_commands), in_function=False)
            self.variables.pop()
        else:
            if else_commands:
                # Thêm một phạm vi mới cho khối ELSE
                self.variables.append({})
                self.interpret('\n'.join(else_commands), in_function=False)
                self.variables.pop()

    def execute_while(self, args, block_commands):
        # Nội dung như trước
        condition_str = args.get('condition')

        # Thêm một phạm vi mới cho vòng lặp WHILE
        self.variables.append({})

        try:
            while self.evaluate_condition(condition_str):
                # Thực thi các lệnh trong block_commands
                try:
                    self.interpret('\n'.join(block_commands), in_function=True)  # in_function=True để hỗ trợ RETURN trong hàm
                except FunctionReturn as fr:
                    # Nếu gặp RETURN, thoát khỏi vòng lặp
                    self.variables.pop()
                    raise fr  # Đẩy ngoại lệ ra ngoài để được xử lý ở cấp độ hàm
        finally:
            # Loại bỏ phạm vi của vòng lặp
            self.variables.pop()

    def parse_class_definition(self, content):
        lines = content.strip().split('\n')
        i = 0
        name = None
        inputs = []
        outputs = []
        code = []
        lib_code = []
        in_env_cal = False
        in_lib = False

        while i < len(lines):
            line = lines[i].strip()
            if not line or line.startswith('#'):
                i += 1
                continue
            if line.startswith('Class '):
                name = line[6:].strip()
                i += 1
            elif line == 'BEGIN':
                i += 1
            elif line == 'IN :':
                i += 1
                while i < len(lines):
                    line = lines[i].strip()
                    if line == 'LIB':
                        in_lib = True
                        break
                    elif line == 'ENV CAL':
                        in_env_cal = True
                        break
                    m = re.match(r'^_(\w+):\s*(.*)$', line)
                    if m:
                        var_type = m.group(1).lower()
                        var_names = [v.strip() for v in m.group(2).split(',')]
                        for var_name in var_names:
                            if var_name:
                                inputs.append((var_type, var_name))
                    i += 1
            elif line == 'LIB':
                in_lib = True
                i += 1
                while i < len(lines):
                    line = lines[i].strip()
                    if line == 'ENV CAL':
                        in_lib = False
                        in_env_cal = True
                        break
                    elif line == 'OUT':
                        in_lib = False
                        break
                    elif line == f'END {name}':
                        in_lib = False
                        break
                    else:
                        lib_code.append(line)
                    i += 1
            elif line == 'ENV CAL':
                in_env_cal = True
                i += 1
                while i < len(lines):
                    line = lines[i].strip()
                    if line == 'OUT':
                        in_env_cal = False
                        break
                    elif line == f'END {name}':
                        in_env_cal = False
                        break
                    else:
                        code.append(line)
                    i += 1
            elif line == 'OUT':
                i += 1
                while i < len(lines):
                    line = lines[i].strip()
                    if line == f'END {name}':
                        break
                    m = re.match(r'^_(\w+):\s*(.*)$', line)
                    if m:
                        var_type = m.group(1).lower()
                        var_names = [v.strip() for v in m.group(2).split(',')]
                        for var_name in var_names:
                            if var_name:
                                outputs.append((var_type, var_name))
                    i += 1
                i += 1
            elif line == f'END {name}':
                break
            else:
                i += 1

        if not name:
            raise InterpreterError("Error: Class name not found in class definition")
        return ClassDefinition(name, inputs, outputs, code, lib_code=lib_code)


    def execute_load(self, args):
        path = args.get('path')
        inputs = args.get('inputs', [])
        saves = args.get('saves', [])

        if not path:
            raise InterpreterError("Error: LOAD command requires --from argument")

        # Read class file
        try:
            with open(path, 'r', encoding="utf8") as f:
                content = f.read()
        except FileNotFoundError:
            raise InterpreterError(f"Error: File '{path}' not found")
        except IOError:
            raise InterpreterError(f"Error: Cannot read file '{path}'")

        # Parse class definition
        class_def = self.parse_class_definition(content)

        # Hiển thị thông tin ClassDefinition
        print(f"Loaded ClassDefinition: {repr(class_def)}")

        # Validate inputs
        if len(inputs) != len(class_def.inputs):
            raise InterpreterError(f"Error: Class '{class_def.name}' expects {len(class_def.inputs)} inputs, got {len(inputs)}")

        # Create new scope for class execution
        class_scope = {}

        for (var_type, var_name), input_var_name in zip(class_def.inputs, inputs):
            var = self.get_variable(input_var_name)
            if var is None:
                raise InterpreterError(f"Error: Variable '{input_var_name}' not defined for class input '{var_name}'")
            if var.type != var_type:
                raise InterpreterError(f"Error: Variable '{input_var_name}' type '{var.type}' does not match expected type '{var_type}' for class input '{var_name}'")
            class_scope[var_name] = Variable(var_type, var_name, var.value)

        # Add class scope to variables stack
        self.variables.append(class_scope)

        # Execute LIB code with local functions
        try:
            if class_def.lib_code:
                self.interpret('\n'.join(class_def.lib_code), in_function=False, local_functions=class_def.functions, class_scope=class_scope)
            # Execute class code with local functions
            self.interpret('\n'.join(class_def.code), in_function=False, local_functions=class_def.functions, class_scope=class_scope)
        except InterpreterError as e:
            raise InterpreterError(f"Error executing class '{class_def.name}': {e}")
        finally:
            # Remove class scope
            self.variables.pop()

        # Validate outputs
        if len(saves) != len(class_def.outputs):
            raise InterpreterError(f"Error: Class '{class_def.name}' produces {len(class_def.outputs)} outputs, but {len(saves)} --save arguments provided")

        # Map outputs
        for (var_type, var_name), save_var_name in zip(class_def.outputs, saves):
            output_var = class_scope.get(var_name)
            if output_var is None:
                raise InterpreterError(f"Error: Output variable '{var_name}' not defined in class '{class_def.name}'")
            existing_var = self.get_variable(save_var_name)
            if existing_var:
                if existing_var.type != var_type:
                    raise InterpreterError(f"Error: Variable '{save_var_name}' type '{existing_var.type}' does not match expected type '{var_type}' for class output '{var_name}'")
                existing_var.value = output_var.value
            else:
                new_var = Variable(var_type, save_var_name, output_var.value)
                self.set_variable(new_var)

        print(f"Class '{class_def.name}' executed and outputs saved to variables: {', '.join(saves)}")

    def display_variables(self):
        """
        Hiển thị tất cả biến toàn cục và biến trong phạm vi hiện tại.
        """
        print(self.functions)
        print("\nFinal Global Variables:")
        for var in self.global_variables.values():
            print(var)
        if len(self.variables) > 1:
            print("\nFinal Variables in Current Scope:")
            for var in self.variables[-1].values():
                print(var)

def main():
    """
    Main function to run the interpreter with a full example script, including class loading.
    """
    # Ví dụ về sử dụng lớp
    code = """
    VAR --type int --name num1 --set 7
    VAR --type int --name num2 --set 3
    LOAD --from MathOperations1.cls --input num1 --input num2 --save sum_out --save product_out
    LOAD --from MathOperations1.cls --input num1 --input product_out --save sum_out --save product_out

    PRI --print sum_out
    PRI --print product_out

    """

    # Tạo một đối tượng Interpreter
    interpreter = Interpreter()

    # Thực thi kịch bản
    interpreter.interpret(code)

    # Hiển thị các biến cuối cùng
    interpreter.display_variables()

if __name__ == "__main__":
    main()
