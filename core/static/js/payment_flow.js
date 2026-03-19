(function (global) {
  const clone = (value) => JSON.parse(JSON.stringify(value));

  const defaultPaymentData = () => ({
    payerName: '',
    planName: '',
    reference: '',
    baseAmount: 0,
    finalAmount: 0,
    discountPercent: 0,
    discountValue: 0,
    finePercent: 0,
    fineValue: 0,
  });

  function parseNumber(value) {
    if (typeof value === 'number') {
      return Number.isFinite(value) ? value : 0;
    }
    if (typeof value === 'string') {
      const normalized = value
        .replace(/[^0-9.,-]+/g, '')
        .replace(/,(?=\d{3}(?:[.,]|$))/g, '')
        .replace(',', '.');
      const parsed = Number.parseFloat(normalized);
      return Number.isFinite(parsed) ? parsed : 0;
    }
    return 0;
  }

  function roundCurrency(value) {
    const num = parseNumber(value);
    return Number((Math.round((num + Number.EPSILON) * 100) / 100).toFixed(2));
  }

  function formatDecimal(value) {
    return roundCurrency(value).toFixed(2);
  }

  function formatCurrency(value) {
    const amount = roundCurrency(value);
    return amount.toLocaleString('pt-BR', {
      style: 'currency',
      currency: 'BRL',
    });
  }

  function createPaymentFlow(options = {}) {
    const initialData = {
      ...defaultPaymentData(),
      ...(options.initialData || {}),
    };

    const flow = {
      dropdown: false,
      alert: false,
      validate: false,
      validationMessage: '',
      validationDifference: 0,
      payments: [],
      discountEnabled: false,
      paymentData: clone(initialData),
      _initialPaymentData: clone(initialData),

      addPayment(methodId, methodLabel, paidOn = null) {
        this.payments.push({
          method_id: methodId,
          payment_method: methodLabel,
          value: '',
          quantity_installments: 1,
          paid_on: paidOn,
        });
        this.dropdown = false;
        if (typeof this.$nextTick === 'function' && typeof lucide !== 'undefined') {
          this.$nextTick(() => lucide.createIcons());
        }
        this.updateValidation();
      },

      removePayment(index) {
        if (index < 0 || index >= this.payments.length) {
          return;
        }
        this.payments.splice(index, 1);
        if (typeof this.$nextTick === 'function' && typeof lucide !== 'undefined') {
          this.$nextTick(() => lucide.createIcons());
        }
        this.updateValidation();
      },

      setPaymentData(partial = {}) {
        const updates = { ...partial };

        if (Object.prototype.hasOwnProperty.call(updates, 'baseAmount')) {
          updates.baseAmount = parseNumber(updates.baseAmount);
        }
        if (Object.prototype.hasOwnProperty.call(updates, 'finalAmount')) {
          updates.finalAmount = parseNumber(updates.finalAmount);
        }
        if (Object.prototype.hasOwnProperty.call(updates, 'discountPercent')) {
          updates.discountPercent = roundCurrency(updates.discountPercent);
        }
        if (Object.prototype.hasOwnProperty.call(updates, 'discountValue')) {
          updates.discountValue = roundCurrency(updates.discountValue);
        }
        if (Object.prototype.hasOwnProperty.call(updates, 'finePercent')) {
          updates.finePercent = roundCurrency(updates.finePercent);
        }
        if (Object.prototype.hasOwnProperty.call(updates, 'fineValue')) {
          updates.fineValue = roundCurrency(updates.fineValue);
        }

        const hasExplicitFinal = Object.prototype.hasOwnProperty.call(updates, 'finalAmount');

        this.paymentData = {
          ...this.paymentData,
          ...updates,
        };

        if (hasExplicitFinal) {
          this.updateValidation();
        } else {
          this.recalculateFinalAmount();
        }
      },

      resetPaymentFlow() {
        this.dropdown = false;
        this.alert = false;
        this.validate = false;
        this.validationMessage = '';
        this.validationDifference = 0;
        this.payments = [];
        this.discountEnabled = false;
        this.paymentData = clone(this._initialPaymentData);
        this.recalculateFinalAmount();
      },

      updateDiscountFromPercent(percentValue) {
        const percent = roundCurrency(Math.max(0, Math.min(100, parseNumber(percentValue))));
        this.paymentData.discountPercent = percent;
        this.recalculateFinalAmount();
      },

      updateDiscountFromValue(value) {
        const base = this.paymentData.baseAmount || 0;
        const discount = roundCurrency(Math.max(0, Math.min(base, parseNumber(value))));
        this.paymentData.discountValue = discount;
        this.recalculateFinalAmount();
      },

      updateFinePercent(value) {
        const percent = Math.max(0, parseNumber(value));
        this.paymentData.finePercent = roundCurrency(percent);
        this.recalculateFinalAmount();
      },

      updateFineValue(value) {
        const fineValue = Math.max(0, parseNumber(value));
        this.paymentData.fineValue = roundCurrency(fineValue);
        this.recalculateFinalAmount();
      },

      applyDiscountEnabled(enabled) {
        this.discountEnabled = Boolean(enabled);
        this.recalculateFinalAmount();
      },

      recalculateFinalAmount() {
        const base = parseNumber(this.paymentData.baseAmount || 0);
        if (!this.discountEnabled) {
          this.paymentData.finalAmount = roundCurrency(base);
          this.updateValidation();
          return;
        }

        let total = roundCurrency(base);
        if (this.paymentData.discountPercent) {
          total = roundCurrency(
            total - roundCurrency(total * (Math.max(0, this.paymentData.discountPercent) / 100)),
          );
        }

        if (this.paymentData.discountValue) {
          total = roundCurrency(total - Math.max(0, this.paymentData.discountValue));
        }

        if (this.paymentData.finePercent) {
          total = roundCurrency(
            total + roundCurrency(total * (Math.max(0, this.paymentData.finePercent) / 100)),
          );
        }

        if (this.paymentData.fineValue) {
          total = roundCurrency(total + Math.max(0, this.paymentData.fineValue));
        }

        this.paymentData.finalAmount = roundCurrency(Math.max(total, 0));

        this.updateValidation();
      },

      updateValidation() {
        const expected = parseNumber(this.paymentData.finalAmount || 0);
        const total = this.payments.reduce(
          (acc, payment) => acc + parseNumber(payment.value),
          0,
        );

        this.validationDifference = roundCurrency(expected - total);

        if (total === 0) {
          this.alert = false;
          this.validate = false;
          this.validationMessage = '';
          return;
        }

        if (this.validationDifference > 0.009) {
          this.alert = true;
          this.validate = false;
          this.validationMessage = `Valor parcial recebido. Restam ${formatCurrency(this.validationDifference)} a serem pagos.`;
          return;
        }

        if (this.validationDifference < -0.009) {
          this.alert = true;
          this.validate = false;
          this.validationMessage = `O valor recebido excede o valor devido em ${formatCurrency(Math.abs(this.validationDifference))}.`;
          return;
        }

        this.alert = false;
        this.validate = true;
        this.validationMessage = '';
      },

      parseNumber,
      round: roundCurrency,
      formatDecimal,
      formatCurrency,
    };

    return flow;
  }

  global.PaymentFlow = {
    createPaymentFlow,
    parseNumber,
    round: roundCurrency,
    formatDecimal,
    formatCurrency,
  };
})(window);
