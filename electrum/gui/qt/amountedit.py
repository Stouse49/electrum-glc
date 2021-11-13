# -*- coding: utf-8 -*-

from decimal import Decimal
from typing import Union

from PyQt5.QtCore import pyqtSignal, Qt, QSize
from PyQt5.QtGui import QPalette, QPainter
from PyQt5.QtWidgets import (QLineEdit, QStyle, QStyleOptionFrame, QSizePolicy)

from .util import char_width_in_lineedit, ColorScheme

from electrum.util import (format_satoshis_plain, decimal_point_to_base_unit_name,
                           FEERATE_PRECISION, quantize_feerate)


class FreezableLineEdit(QLineEdit):
    frozen = pyqtSignal()

    def setFrozen(self, b):
        self.setReadOnly(b)
        self.setFrame(not b)
        self.frozen.emit()


class SizedFreezableLineEdit(FreezableLineEdit):

    def __init__(self, *, width: int, parent=None):
        super().__init__(parent)
        self._width = width
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.setMaximumWidth(width)

    def sizeHint(self) -> QSize:
        sh = super().sizeHint()
        return QSize(self._width, sh.height())


class AmountEdit(SizedFreezableLineEdit):
    shortcut = pyqtSignal()

    def __init__(self, base_unit, is_int=False, parent=None):
        # This seems sufficient for hundred-GLC amounts with 8 decimals
        width = 16 * char_width_in_lineedit()
        super().__init__(width=width, parent=parent)
        self.base_unit = base_unit
        self.textChanged.connect(self.numbify)
        self.is_int = is_int
        self.is_shortcut = False
        self.extra_precision = 0

    def decimal_point(self):
        return 8

    def max_precision(self):
        return self.decimal_point() + self.extra_precision

    def numbify(self):
        text = self.text().strip()
        if text == '!':
            self.shortcut.emit()
            return
        pos = self.cursorPosition()
        chars = '0123456789'
        if not self.is_int: chars +='.'
        s = ''.join([i for i in text if i in chars])
        if not self.is_int:
            if '.' in s:
                p = s.find('.')
                s = s.replace('.','')
                s = s[:p] + '.' + s[p:p+self.max_precision()]
        self.setText(s)
        # setText sets Modified to False.  Instead we want to remember
        # if updates were because of user modification.
        self.setModified(self.hasFocus())
        self.setCursorPosition(pos)

    def paintEvent(self, event):
        QLineEdit.paintEvent(self, event)
        if self.base_unit:
            panel = QStyleOptionFrame()
            self.initStyleOption(panel)
            textRect = self.style().subElementRect(QStyle.SE_LineEditContents, panel, self)
            textRect.adjust(2, 0, -10, 0)
            painter = QPainter(self)
            painter.setPen(ColorScheme.GRAY.as_color())
            painter.drawText(textRect, int(Qt.AlignRight | Qt.AlignVCenter), self.base_unit())

    def get_amount(self) -> Union[None, Decimal, int]:
        try:
            return (int if self.is_int else Decimal)(str(self.text()))
        except:
            return None

    def setAmount(self, x):
        self.setText("%d"%x)


class BTCAmountEdit(AmountEdit):

    def __init__(self, decimal_point, is_int=False, parent=None):
        AmountEdit.__init__(self, self._base_unit, is_int, parent)
        self.decimal_point = decimal_point

    def _base_unit(self):
        return decimal_point_to_base_unit_name(self.decimal_point())

    def get_amount(self):
        # returns amt in satoshis
        try:
            x = Decimal(str(self.text()))
        except:
            return None
        # scale it to max allowed precision, make it an int
        power = pow(10, self.max_precision())
        max_prec_amount = int(power * x)
        # if the max precision is simply what unit conversion allows, just return
        if self.max_precision() == self.decimal_point():
            return max_prec_amount
        # otherwise, scale it back to the expected unit
        amount = Decimal(max_prec_amount) / pow(10, self.max_precision()-self.decimal_point())
        return Decimal(amount) if not self.is_int else int(amount)

    def setAmount(self, amount_sat):
        if amount_sat is None:
            self.setText(" ")  # Space forces repaint in case units changed
        else:
            self.setText(format_satoshis_plain(amount_sat, decimal_point=self.decimal_point()))
        self.repaint()  # macOS hack for #6269


class FeerateEdit(BTCAmountEdit):

    def __init__(self, decimal_point, is_int=False, parent=None):
        super().__init__(decimal_point, is_int, parent)
        self.extra_precision = FEERATE_PRECISION

    def _base_unit(self):
        return 'sat/byte'

    def get_amount(self):
        sat_per_byte_amount = BTCAmountEdit.get_amount(self)
        return quantize_feerate(sat_per_byte_amount)

    def setAmount(self, amount):
        amount = quantize_feerate(amount)
        super().setAmount(amount)
