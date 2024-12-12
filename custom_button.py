from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QPushButton

class CustomButton1_trans(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        
        # 初始样式
        self.setStyleSheet('''
            background: white;
            color: white;
            font-size: 20px;
            border-radius: 8px;
            
            cursor: pointer;
            box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.2);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        ''')
   
        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        # Hover effect (simulating :hover)
        if obj == self:
            if event.type() == 2:  # Mouse press event (simulating :active)
                self.setStyleSheet('''
                    background: white;
                    color: white;
                    font-size: 20px;
                    border-radius: 8px;
                    cursor: pointer;
                    box-shadow: 0px 2px 4px rgba(0, 0, 0, 0.2);
                ''')

        return super().eventFilter(obj, event)


class CustomButton1(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        
        # 初始样式
        self.setStyleSheet('''
            background: #009846;
            color: white;
            font-size: 20px;
            border-radius: 8px;
            
            cursor: pointer;
            box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.2);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        ''')
   
        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        # Hover effect (simulating :hover)
        if obj == self:
            if event.type() == 2:  # Mouse press event (simulating :active)
                self.setStyleSheet('''
                    background: #006d2e;
                    color: white;
                    font-size: 20px;
                    border-radius: 8px;
                    cursor: pointer;
                    box-shadow: 0px 2px 4px rgba(0, 0, 0, 0.2);
                ''')

        return super().eventFilter(obj, event)

class CustomButton1_false(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        
        self.setStyleSheet('''
            background: grey;
            color: white;
            font-size: 20px;
            border-radius: 8px;
            
            cursor: pointer;
            box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.2);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        ''')

class CustomButton2(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        
        self.setStyleSheet('''
            background: #006d2e;
            color: white;
            font-size: 18px;
            border-radius: 8px;
            padding: 10px;
            cursor: pointer;
            box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.2);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        ''')

   
        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        # Hover effect (simulating :hover)
        if obj == self:
            if event.type() == 2:  # Mouse press event (simulating :active)
                self.setStyleSheet('''
                    background: #009846;
                    color: white;
                    font-size: 18px;
                    padding: 10px;
                    border-radius: 8px;
                    cursor: pointer;
                    box-shadow: 0px 2px 4px rgba(0, 0, 0, 0.2);
                ''')

        return super().eventFilter(obj, event)
    
class CustomButton2_false(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        
        self.setStyleSheet('''
            background: grey;
            color: white;
            font-size: 18px;
            border-radius: 8px;
            padding: 10px;
            cursor: pointer;
            box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.2);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        ''')

