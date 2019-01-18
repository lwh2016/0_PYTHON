import cantools
import xlsxwriter
import re
from GetTargetFile import GetTargetFile


class DecodedDbc(object):
    def __init__(self, dbcFile):
        self.dbc = cantools.database.load_file(dbcFile)

    def writeToExcel(self, table, sheet):
        chartHeadListMsg = [
            'Msg Name', 'Msg ID', 'Msg Length', 'Tx Node', 'Send Type',
            'Cycle Time', 'Rx Node'
        ]

        chartHeadListSig = [
            'Singals', 'Data Type', 'offset', 'Unit', 'Min Value', 'Max Value',
            'Singal Comment', 'Singal Dis'
        ]
        chartHeadFormatMsg = {
            'bg_color': '#95B3D7',
            'font_name': 'Arial',
            'font_size': '12',
            'align': 'center',
            'valign': 'vcenter',
            'border': True
        }
        chartHeadFormatSig = {
            'bg_color': '#F0F0F0',
            'font_name': 'Arial',
            'font_size': '12',
            'align': 'center',
            'valign': 'vcenter',
            'border': True
        }
        sheet.set_row(0, 40)
        sheet.set_column('A:A', 35)
        sheet.set_column('B:G', 15)
        sheet.set_column('H:H', 40)
        sheet.set_column('I:M', 15)
        sheet.set_column('N:N', 70)
        sheet.set_column('O:O', 45)

        chartHeadFormatMsg = table.add_format(chartHeadFormatMsg)
        sheet.write_row(0, 0, chartHeadListMsg, chartHeadFormatMsg)

        colSigs = len(chartHeadListMsg)
        chartHeadFormatSig = table.add_format(chartHeadFormatSig)
        sheet.write_row(0, colSigs, chartHeadListSig, chartHeadFormatSig)
        curLine = 1

        MsgListFormat = {
            'font_name': 'Arial',
            'font_size': '10',
            'align': 'center',
            'valign': 'vcenter',
            'border': True
        }

        MsgListFormat = table.add_format(MsgListFormat)

        SigListFormat = {
            'font_name': 'Arial',
            'font_size': '10',
            'align': 'center',
            'valign': 'vcenter',
            'border': True
        }

        SigListFormat = table.add_format(SigListFormat)

        for msg in self.dbc.messages:
            msgAttrList = []
            msgAttrList.append(msg.name)
            msgAttrList.append(hex(msg.frame_id))
            msgAttrList.append(msg.length)
            msgAttrList.append(str(msg.senders))
            msgAttrList.append(msg.send_type)
            msgAttrList.append(msg.cycle_time)
            msgAttrList.append(str(msg.signals[0].receivers))
            # print(msgAttrList)
            sheet.write_row(curLine, 0, msgAttrList, MsgListFormat)
            for sig in msg.signals:
                sigAttrList = []
                sigAttrList.append(sig.name)
                if sig.is_float:
                    dataType = 'Float'
                else:
                    if sig.is_signed:
                        dataType = 'Signed'
                    else:
                        dataType = 'Unsigned'
                sigAttrList.append(dataType)
                sigAttrList.append(float(sig.offset) / float(sig.scale))
                sigAttrList.append(sig.unit)
                try:
                    sigAttrList.append(float(sig.minimum) / float(sig.scale))
                    sigAttrList.append(float(sig.maximum) / float(sig.scale))
                except TypeError as e:
                    sigAttrList.append(0)
                    sigAttrList.append(0)

                sigAttrList.append(sig.comment)
                # sigAttrList.append(sig.choices)
                # print(sigAttrList)
                sheet.write_row(curLine, colSigs, sigAttrList, SigListFormat)
                curLine += 1


def main():
    dbcHandler = GetTargetFile('.dbc')
    dbcFileList = dbcHandler.getTarFile()

    excelTable = xlsxwriter.Workbook('DbcExcel.xlsx')

    for dbcfile in dbcFileList:
        sheetName = str(dbcfile).split('.')[0].split('\\')[-1]
        sheetName = re.split(r'[-_]', sheetName)
        sheetName = list(
            filter(lambda x: ('CAN' in x) | ('Sec' in x) | ('FSDA' in x),
                   sheetName))[0]
        print('*****DBC File %s is ready to decode*****\n' % sheetName)
        workSheet = excelTable.add_worksheet(sheetName)
        dbc = DecodedDbc(dbcfile)
        dbc.writeToExcel(excelTable, workSheet)
        print('*****DBC File %s decoded  successfully*****\n' % sheetName)
    excelTable.close()
    print('All Dbc Files decoded  successfully')


if __name__ == '__main__':
    main()
