import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Modal,
  TouchableOpacity,
  TextInput,
  ActivityIndicator,
  Alert,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
  Image,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTranslation } from 'react-i18next';

interface PaymentModalProps {
  visible: boolean;
  amount: number;
  currency?: string;
  onClose: () => void;
  onPaymentSuccess: (transactionData: any) => void;
  processPayment: (paymentData: any) => Promise<any>;
}

type PaymentMethod = 'select' | 'card' | 'mpesa';

export default function PaymentModal({
  visible,
  amount,
  currency = 'TSH',
  onClose,
  onPaymentSuccess,
  processPayment,
}: PaymentModalProps) {
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>('select');
  const [processing, setProcessing] = useState(false);
  const { t } = useTranslation();

  // Card payment state
  const [cardNumber, setCardNumber] = useState('');
  const [cardHolder, setCardHolder] = useState('');
  const [cardExpiry, setCardExpiry] = useState('');
  const [cardCVV, setCardCVV] = useState('');
  const [cardType, setCardType] = useState<'visa' | 'mastercard' | null>(null);

  // M-Pesa payment state
  const [phoneNumber, setPhoneNumber] = useState('');

  const resetForm = () => {
    setPaymentMethod('select');
    setCardNumber('');
    setCardHolder('');
    setCardExpiry('');
    setCardCVV('');
    setPhoneNumber('');
    setCardType(null);
    setProcessing(false);
  };

  const handleClose = () => {
    if (!processing) {
      resetForm();
      onClose();
    }
  };

  const detectCardType = (number: string) => {
    const cleaned = number.replace(/\s/g, '');
    if (cleaned.startsWith('4')) {
      return 'visa';
    } else if (/^5[1-5]/.test(cleaned) || /^2[2-7]/.test(cleaned)) {
      return 'mastercard';
    }
    return null;
  };

  const formatCardNumber = (text: string) => {
    // Remove all non-digits
    const cleaned = text.replace(/\D/g, '');
    // Detect card type
    setCardType(detectCardType(cleaned));
    // Add space every 4 digits
    const formatted = cleaned.match(/.{1,4}/g)?.join(' ') || cleaned;
    return formatted.substring(0, 19); // Max 16 digits + 3 spaces
  };

  const formatExpiry = (text: string) => {
    // Remove all non-digits
    const cleaned = text.replace(/\D/g, '');
    // Add slash after 2 digits
    if (cleaned.length >= 2) {
      return `${cleaned.substring(0, 2)}/${cleaned.substring(2, 4)}`;
    }
    return cleaned;
  };

  const formatPhone = (text: string) => {
    // Ensure it starts with +255
    if (!text.startsWith('+255')) {
      return '+255' + text.replace(/\D/g, '').substring(0, 9);
    }
    return '+255' + text.substring(4).replace(/\D/g, '').substring(0, 9);
  };

  const handleCardPayment = async () => {
    // Validation
    const cleanCard = cardNumber.replace(/\s/g, '');
    if (cleanCard.length < 13) {
      Alert.alert(t('paymentModal.invalidCard'), t('paymentModal.invalidCardMsg'));
      return;
    }
    if (!cardHolder.trim()) {
      Alert.alert(t('common.error'), t('paymentModal.invalidCardholderMsg'));
      return;
    }
    if (cardExpiry.length !== 5) {
      Alert.alert(t('paymentModal.invalidExpiry'), t('paymentModal.invalidExpiryMsg'));
      return;
    }
    if (cardCVV.length < 3) {
      Alert.alert(t('paymentModal.invalidCVV'), t('paymentModal.invalidCVVMsg'));
      return;
    }

    try {
      setProcessing(true);
      const result = await processPayment({
        amount,
        payment_type: 'card',
        card_number: cleanCard,
        card_holder: cardHolder,
        card_expiry: cardExpiry,
        card_cvv: cardCVV,
      });

      console.log('Card payment result:', result);
      if (result.success) {
        console.log('Card payment success, calling onPaymentSuccess');
        resetForm();
        // Let parent handle closing payment modal and opening screenshot modal
        onPaymentSuccess(result);
      } else {
        Alert.alert(t('paymentModal.paymentFailed'), result.error || t('paymentModal.paymentFailedMsg'));
      }
    } catch (error: any) {
      console.error('Card payment error:', error);
      Alert.alert(
        t('paymentModal.paymentError'),
        error.response?.data?.error || t('paymentModal.paymentErrorMsg')
      );
    } finally {
      setProcessing(false);
    }
  };

  const handleMPesaPayment = async () => {
    // Validation
    if (phoneNumber.length < 13) {
      Alert.alert(t('paymentModal.invalidPhone'), t('paymentModal.invalidPhoneMsg'));
      return;
    }

    try {
      setProcessing(true);
      const result = await processPayment({
        amount,
        payment_type: 'mpesa',
        phone_number: phoneNumber,
      });

      console.log('Mobile money payment result:', result);
      if (result.success) {
        console.log('Mobile money payment success, calling onPaymentSuccess');
        resetForm();
        // Let parent handle closing payment modal and opening screenshot modal
        onPaymentSuccess(result);
      } else {
        Alert.alert(t('paymentModal.paymentFailed'), result.error || t('paymentModal.paymentFailedMsg'));
      }
    } catch (error: any) {
      console.error('M-Pesa payment error:', error);
      Alert.alert(
        t('paymentModal.paymentError'),
        error.response?.data?.error || t('paymentModal.paymentErrorMsg')
      );
    } finally {
      setProcessing(false);
    }
  };

  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent={true}
      onRequestClose={handleClose}
    >
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.container}
      >
        <View style={styles.overlay}>
          <View style={styles.modal}>
            {/* Header */}
            <View style={styles.header}>
              <Text style={styles.headerTitle}>{t('paymentModal.title')}</Text>
              <TouchableOpacity onPress={handleClose} disabled={processing}>
                <Ionicons name="close" size={24} color="#666" />
              </TouchableOpacity>
            </View>

            {/* Amount Display */}
            <View style={styles.amountContainer}>
              <Text style={styles.amountLabel}>{t('paymentModal.totalAmount')}</Text>
              <Text style={styles.amountValue}>
                {currency} {amount.toFixed(2)}
              </Text>
            </View>

            <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
              {/* Payment Method Selection */}
              {paymentMethod === 'select' && (
                <View style={styles.methodsContainer}>
                  <Text style={styles.sectionTitle}>{t('paymentModal.selectMethod')}</Text>

                  <TouchableOpacity
                    style={styles.methodButton}
                    onPress={() => setPaymentMethod('card')}
                  >
                    <View style={styles.methodIcon}>
                      <Ionicons name="card" size={32} color="#14b8a6" />
                    </View>
                    <View style={styles.methodInfo}>
                      <Text style={styles.methodTitle}>{t('paymentModal.creditCard')}</Text>
                      <Text style={styles.methodSubtitle}>{t('paymentModal.visaMastercard')}</Text>
                    </View>
                    <Ionicons name="chevron-forward" size={24} color="#999" />
                  </TouchableOpacity>

                  <TouchableOpacity
                    style={styles.methodButton}
                    onPress={() => setPaymentMethod('mpesa')}
                  >
                    <View style={styles.methodIcon}>
                      <Ionicons name="phone-portrait" size={32} color="#14b8a6" />
                    </View>
                    <View style={styles.methodInfo}>
                      <Text style={styles.methodTitle}>{t('paymentModal.mobileMoney')}</Text>
                      <Text style={styles.methodSubtitle}>{t('paymentModal.mobilePesaOptions')}</Text>
                    </View>
                    <Ionicons name="chevron-forward" size={24} color="#999" />
                  </TouchableOpacity>

                  <View style={styles.demoNotice}>
                    <Ionicons name="information-circle" size={20} color="#14b8a6" />
                    <Text style={styles.demoText}>
                      Demo Mode: Use test credentials{'\n'}
                      Visa: 4242 4242 4242 4242{'\n'}
                      Mastercard: 5555 5555 5555 5555{'\n'}
                      Mobile Money: +255123456789
                    </Text>
                  </View>
                </View>
              )}

              {/* Card Payment Form */}
              {paymentMethod === 'card' && (
                <View style={styles.form}>
                  <TouchableOpacity
                    style={styles.backButton}
                    onPress={() => setPaymentMethod('select')}
                    disabled={processing}
                  >
                    <Ionicons name="arrow-back" size={20} color="#14b8a6" />
                    <Text style={styles.backText}>{t('common.back')}</Text>
                  </TouchableOpacity>

                  <Text style={styles.sectionTitle}>{t('paymentModal.cardDetails')}</Text>

                  <View style={styles.inputGroup}>
                    <Text style={styles.label}>{t('paymentModal.cardNumber')}</Text>
                    <View style={styles.inputWithIcon}>
                      <TextInput
                        style={[styles.input, cardType && styles.inputWithCardIcon]}
                        placeholder="4242 4242 4242 4242 or 5555 5555 5555 5555"
                        keyboardType="numeric"
                        value={cardNumber}
                        onChangeText={(text) => setCardNumber(formatCardNumber(text))}
                        maxLength={19}
                        editable={!processing}
                      />
                      {cardType && (
                        <View style={styles.cardIconContainer}>
                          {cardType === 'visa' && (
                            <View style={styles.visaLogo}>
                              <Text style={styles.visaText}>VISA</Text>
                            </View>
                          )}
                          {cardType === 'mastercard' && (
                            <View style={styles.mastercardLogo}>
                              <View style={[styles.circle, styles.circleRed]} />
                              <View style={[styles.circle, styles.circleOrange]} />
                            </View>
                          )}
                        </View>
                      )}
                    </View>
                  </View>

                  <View style={styles.inputGroup}>
                    <Text style={styles.label}>{t('paymentModal.cardholderName')}</Text>
                    <TextInput
                      style={styles.input}
                      placeholder="John Doe"
                      value={cardHolder}
                      onChangeText={setCardHolder}
                      autoCapitalize="words"
                      editable={!processing}
                    />
                  </View>

                  <View style={styles.row}>
                    <View style={[styles.inputGroup, styles.flex1]}>
                      <Text style={styles.label}>{t('paymentModal.expiryDate')}</Text>
                      <TextInput
                        style={styles.input}
                        placeholder="MM/YY"
                        keyboardType="numeric"
                        value={cardExpiry}
                        onChangeText={(text) => setCardExpiry(formatExpiry(text))}
                        maxLength={5}
                        editable={!processing}
                      />
                    </View>

                    <View style={[styles.inputGroup, styles.flex1, styles.marginLeft]}>
                      <Text style={styles.label}>CVV</Text>
                      <TextInput
                        style={styles.input}
                        placeholder="123"
                        keyboardType="numeric"
                        value={cardCVV}
                        onChangeText={(text) => setCardCVV(text.replace(/\D/g, '').substring(0, 4))}
                        maxLength={4}
                        secureTextEntry
                        editable={!processing}
                      />
                    </View>
                  </View>

                  <TouchableOpacity
                    style={[styles.payButton, processing && styles.payButtonDisabled]}
                    onPress={handleCardPayment}
                    disabled={processing}
                  >
                    {processing ? (
                      <ActivityIndicator color="#fff" />
                    ) : (
                      <>
                        <Ionicons name="card" size={20} color="#fff" />
                        <Text style={styles.payButtonText}>
                          {t('paymentModal.payAmount', { currency, amount: amount.toFixed(2) })}
                        </Text>
                      </>
                    )}
                  </TouchableOpacity>
                </View>
              )}

              {paymentMethod === 'mpesa' && (
                <View style={styles.form}>
                  <TouchableOpacity
                    style={styles.backButton}
                    onPress={() => setPaymentMethod('select')}
                    disabled={processing}
                  >
                    <Ionicons name="arrow-back" size={20} color="#14b8a6" />
                    <Text style={styles.backText}>{t('common.back')}</Text>
                  </TouchableOpacity>

                  <Text style={styles.sectionTitle}>{t('paymentModal.mobileMoneyPayment')}</Text>

                  <View style={styles.inputGroup}>
                    <Text style={styles.label}>{t('paymentModal.mobileMoneyPhone')}</Text>
                    <TextInput
                      style={styles.input}
                      placeholder="+255123456789"
                      keyboardType="phone-pad"
                      value={phoneNumber}
                      onChangeText={(text) => setPhoneNumber(formatPhone(text))}
                      maxLength={13}
                      editable={!processing}
                    />
                    <Text style={styles.hint}>
                      {t('paymentModal.mobilePhoneHint')}
                    </Text>
                  </View>

                  <View style={styles.mpesaInfo}>
                    <Ionicons name="information-circle" size={20} color="#14b8a6" />
                    <Text style={styles.mpesaInfoText}>
                      {t('paymentModal.mobileMoneyPrompt')}
                    </Text>
                  </View>

                  <TouchableOpacity
                    style={[styles.payButton, processing && styles.payButtonDisabled]}
                    onPress={handleMPesaPayment}
                    disabled={processing}
                  >
                    {processing ? (
                      <ActivityIndicator color="#fff" />
                    ) : (
                      <>
                        <Ionicons name="phone-portrait" size={20} color="#fff" />
                        <Text style={styles.payButtonText}>
                          {t('paymentModal.payAmount', { currency, amount: amount.toFixed(2) })}
                        </Text>
                      </>
                    )}
                  </TouchableOpacity>
                </View>
              )}
            </ScrollView>
          </View>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'flex-end',
  },
  modal: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    maxHeight: '90%',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: '#333',
  },
  amountContainer: {
    padding: 20,
    backgroundColor: '#f8f9fa',
    alignItems: 'center',
  },
  amountLabel: {
    fontSize: 14,
    color: '#666',
    marginBottom: 4,
  },
  amountValue: {
    fontSize: 32,
    fontWeight: '700',
    color: '#14b8a6',
  },
  content: {
    padding: 20,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginBottom: 16,
  },
  methodsContainer: {
    paddingBottom: 20,
  },
  methodButton: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    backgroundColor: '#f8f9fa',
    borderRadius: 12,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  methodIcon: {
    width: 50,
    height: 50,
    borderRadius: 25,
    backgroundColor: '#e6f7f5',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 16,
  },
  methodInfo: {
    flex: 1,
  },
  methodTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 4,
  },
  methodSubtitle: {
    fontSize: 14,
    color: '#666',
  },
  demoNotice: {
    flexDirection: 'row',
    padding: 16,
    backgroundColor: '#e6f7f5',
    borderRadius: 8,
    marginTop: 12,
  },
  demoText: {
    flex: 1,
    fontSize: 12,
    color: '#0f766e',
    marginLeft: 8,
    lineHeight: 18,
  },
  form: {
    paddingBottom: 20,
  },
  backButton: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
  },
  backText: {
    fontSize: 16,
    color: '#14b8a6',
    marginLeft: 4,
  },
  inputGroup: {
    marginBottom: 16,
  },
  label: {
    fontSize: 14,
    fontWeight: '500',
    color: '#333',
    marginBottom: 8,
  },
  input: {
    borderWidth: 1,
    borderColor: '#e5e7eb',
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
    color: '#333',
    backgroundColor: '#fff',
  },
  inputWithIcon: {
    position: 'relative',
  },
  inputWithCardIcon: {
    paddingRight: 100,
  },
  cardIconContainer: {
    position: 'absolute',
    right: 8,
    top: 8,
    bottom: 8,
    justifyContent: 'center',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
    backgroundColor: '#ffffff',
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  visaLogo: {
    backgroundColor: '#1A1F71',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 4,
    height: 28,
    justifyContent: 'center',
    alignItems: 'center',
  },
  visaText: {
    color: '#ffffff',
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 1.5,
  },
  mastercardLogo: {
    flexDirection: 'row',
    alignItems: 'center',
    width: 45,
    height: 28,
    justifyContent: 'center',
    position: 'relative',
  },
  circle: {
    width: 20,
    height: 20,
    borderRadius: 10,
    position: 'absolute',
  },
  circleRed: {
    backgroundColor: '#EB001B',
    left: 0,
  },
  circleOrange: {
    backgroundColor: '#FF5F00',
    right: 0,
    opacity: 0.9,
  },
  hint: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
  },
  row: {
    flexDirection: 'row',
  },
  flex1: {
    flex: 1,
  },
  marginLeft: {
    marginLeft: 12,
  },
  mpesaInfo: {
    flexDirection: 'row',
    padding: 12,
    backgroundColor: '#e6f7f5',
    borderRadius: 8,
    marginBottom: 16,
  },
  mpesaInfoText: {
    flex: 1,
    fontSize: 13,
    color: '#0f766e',
    marginLeft: 8,
    lineHeight: 18,
  },
  payButton: {
    backgroundColor: '#14b8a6',
    padding: 16,
    borderRadius: 12,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 8,
  },
  payButtonDisabled: {
    opacity: 0.6,
  },
  payButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
    marginLeft: 8,
  },
});
