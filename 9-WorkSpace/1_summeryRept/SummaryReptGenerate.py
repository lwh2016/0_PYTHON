import xlsxwriter


def Pos_Letter2Num(Posletter):
    rowIndex = int(Posletter[1:len(Posletter)]) - 1
    colIndex = int(ord(Posletter[0])) - 65
    return rowIndex, colIndex


def Pos_Num2Letter(rowIndex, colIndex):
    L1 = str(chr(colIndex + 65))
    L2 = str(rowIndex + 1)
    return L1 + L2


class SummaryRept(object):
    def __init__(self, name='00TestSummaryReport.xlsx'):
        self.__xlsxFile = xlsxwriter.Workbook(name)
        self.__sheet = self.__xlsxFile.add_worksheet(name)
        self.__sheet.set_row(0, 40)
        self.__sheet.set_column('A:A', 5)
        self.__sheet.set_column('B:G', 20)

    def GenerateRept(self):
        title_0 = title('Software Integration Testing Report', 0, self.__sheet,
                        self.__xlsxFile)
        next_Pos = title_0.writeTitle('A1')

        title_1 = title('1. Test basic information', 1, self.__sheet,
                        self.__xlsxFile)
        next_Pos = title_1.writeTitle(next_Pos)

        chart_1 = chart1(self.__sheet, self.__xlsxFile)
        next_Pos = chart_1.writeChart(next_Pos)

        title_2 = title('2. Test result summary', 1, self.__sheet,
                        self.__xlsxFile)
        next_Pos = title_2.writeTitle(next_Pos)

        chart_2 = chart2(self.__sheet, self.__xlsxFile)
        next_Pos = chart_2.writeChart(next_Pos)

        title_3 = title('3. Test data', 1, self.__sheet, self.__xlsxFile)
        next_Pos = title_3.writeTitle(next_Pos)

        title_3_1 = title('3.1. Test items', 2, self.__sheet, self.__xlsxFile)
        next_Pos = title_3_1.writeTitle(next_Pos)

        print(next_Pos)

        self.__xlsxFile.close()


class title(object):
    def __init__(self, title, titleLevel, sheet, xlsxFile):
        self.__title = title
        self.__titleLevel = titleLevel
        self.__sheet = sheet
        self.__xlsxFile = xlsxFile

    def titleStyle(self):
        if self.__titleLevel == 0:
            titleFormat = {
                'bg_color': '#95B3D7',
                'font_name': 'Arial',
                'font_size': '14',
                'align': 'center',
                'valign': 'vcenter'
            }
        elif self.__titleLevel == 1:
            titleFormat = {
                'font_name': 'Arial',
                'font_size': '11',
                'bold': True
            }
        elif self.__titleLevel == 2:
            titleFormat = {
                'font_name': 'Arial',
                'font_size': '11',
                'bold': True,
                'italic': True
            }
        else:
            raise Exception('Title Level only support 0,1,2')
        return titleFormat

    def writeTitle(self, TitlePosition):
        style = self.titleStyle()
        title_style = self.__xlsxFile.add_format(style)
        if self.__titleLevel == 0:
            TitlePosition = 'A1:G1'
            self.__sheet.merge_range(TitlePosition, self.__title, title_style)
            return 'A3'
        else:
            self.__sheet.write(TitlePosition, self.__title, title_style)
            r, c = Pos_Letter2Num(TitlePosition)
            return Pos_Num2Letter(r + 1, c)


class chart1(object):
    def __init__(self, sheet, xlsxFile):
        self.__sheet = sheet
        self.__xlsxFile = xlsxFile
        self.__chart = [[
            'Test spec version', '', 'Test case version', '', 'Test round', ''
        ], ['SwReq version', '', 'Environment', '', 'Vehicle No', '-'],
                        ['SW version', '', 'Test date', '', 'Responsible', ''],
                        ['Test result', 'fail']]
        self.ChartData()

    def ChartData(self):
        pass

    def getChartSize(self):
        numRow = len(self.__chart)
        numCol = max([len(row) for row in self.__chart])
        return numRow, numCol

    def writeChart(self, startPosition):
        rowNum, colNum = self.getChartSize()
        rowIndex, colIndex = Pos_Letter2Num(startPosition)
        colIndex = colIndex + 1
        style1 = {'font_name': 'Arial', 'font_size': '10', 'border': True}
        style1 = self.__xlsxFile.add_format(style1)
        for row in self.__chart:
            if len(row) == colNum:
                self.__sheet.write_row(rowIndex, colIndex, row, style1)
                rowIndex = rowIndex + 1
            else:
                currentPos = Pos_Num2Letter(rowIndex, colIndex)
                self.__sheet.write(currentPos, row[0], style1)
                pass_style = {
                    'bg_color': '#228B22',
                    'font_name': 'Arial',
                    'font_size': '10',
                    'italic': True,
                    'border': True
                }
                fail_style = {
                    'bg_color': '#FF0000',
                    'font_name': 'Arial',
                    'font_size': '10',
                    'italic': True,
                    'border': True
                }
                s_pos = Pos_Num2Letter(rowIndex, colIndex + 1)
                e_pos = Pos_Num2Letter(rowIndex, colIndex + 5)
                l_pos = s_pos + ':' + e_pos
                if row[1] == 'pass':
                    style = self.__xlsxFile.add_format(pass_style)
                else:
                    style = self.__xlsxFile.add_format(fail_style)
                self.__sheet.merge_range(l_pos, row[1], style)
                rowIndex = rowIndex + 1
        return Pos_Num2Letter(rowIndex + 1, colIndex - 1)


class chart2(object):
    def __init__(self, sheet, xlsxFile):
        self.__sheet = sheet
        self.__xlsxFile = xlsxFile
        self.__chart = [['Test summary result', ''], ['Total cases', ''],
                        ['Test passed', ''], ['Test failed rate', '']]
        self.ChartData()

    def ChartData(self):
        pass

    def getChartSize(self):
        numRow = len(self.__chart)
        numCol = max([len(row) for row in self.__chart])
        return numRow, numCol

    def writeChart(self, startPosition):
        rowNum, colNum = self.getChartSize()
        rowIndex, colIndex = Pos_Letter2Num(startPosition)
        colIndex = colIndex + 1
        style1 = {'font_name': 'Arial', 'font_size': '10', 'border': True}
        style1 = self.__xlsxFile.add_format(style1)
        for i in range(rowNum):
            self.__sheet.write(rowIndex, colIndex, self.__chart[i][0], style1)
            s_pos = Pos_Num2Letter(rowIndex, colIndex + 1)
            e_pos = Pos_Num2Letter(rowIndex, colIndex + 5)
            l_pos = s_pos + ':' + e_pos
            self.__sheet.merge_range(l_pos, self.__chart[i][1], style1)
            rowIndex = rowIndex + 1
        return Pos_Num2Letter(rowIndex + 1, colIndex - 1)


class chart3_1(object):
    _counter = 0

    def __init__(self, sheet, xlsxFile):
        _counter += 1
        self.__sheet = sheet
        self.__xlsxFile = xlsxFile
        self.__chartHead = [
            'No.', 'Test Category', 'Test case name', 'Selected or not',
            'Test Result', 'Nodes'
        ]
        HeadStyle = {'font_name': 'Arial', 'font_size': '10', 'border': True}
        HeadStyle = self.__xlsxFile.add_format(HeadStyle)
        self.ChartData()

    def ChartData(self):
        pass

    def writeChart(self, startPosition):
        rowNum, colNum = self.getChartSize()
        rowIndex, colIndex = Pos_Letter2Num(startPosition)
        if chart3_1._counter == 1:
            self.__sheet.write_row


def main():
    sumRept = SummaryRept()
    sumRept.GenerateRept()


if __name__ == '__main__':
    main()
