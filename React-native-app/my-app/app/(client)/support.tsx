import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  Alert,
  Linking,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../../components/Header';
import { useTranslation } from 'react-i18next';

interface FAQ {
  id: number;
  question: string;
  answer: string;
}

export default function SupportScreen() {
  const { t } = useTranslation();
  const { theme } = useTheme();
  const [expandedFAQ, setExpandedFAQ] = useState<number | null>(null);
  const [contactSubject, setContactSubject] = useState('');
  const [contactMessage, setContactMessage] = useState('');

  const faqs: FAQ[] = [
    {
      id: 1,
      question: 'How do I post a service request?',
      answer: 'Tap "Request Service" from your dashboard or the quick actions menu. Fill in the service type, description, location, and budget, then submit.',
    },
    {
      id: 2,
      question: 'How do I find and hire a worker?',
      answer: 'Use the Search tab to browse workers by category or skill. View their profile, ratings, and reviews, then send them a direct hire request.',
    },
    {
      id: 3,
      question: 'How do I make a payment?',
      answer: 'Once a worker completes a job, you will be prompted to release payment. You can pay via mobile money, bank transfer, or other linked payment methods.',
    },
    {
      id: 4,
      question: 'How do I rate a worker?',
      answer: 'After a job is marked complete, you will receive a prompt to rate and review the worker. You can also rate them from your job history.',
    },
    {
      id: 5,
      question: 'What if the worker does not show up?',
      answer: 'Contact our support team immediately. We will help mediate and, if necessary, help you find a replacement worker as quickly as possible.',
    },
    {
      id: 6,
      question: 'How do I cancel a service request?',
      answer: 'Open the service request from My Requests, tap the menu icon, and select Cancel. Note that cancellation policies may apply depending on the job status.',
    },
    {
      id: 7,
      question: 'How do I update my payment method?',
      answer: 'Go to Profile, then Payment Methods. You can add, edit, or remove payment methods from there.',
    },
    {
      id: 8,
      question: 'Is my payment information secure?',
      answer: 'Yes. All payment data is encrypted and we never store full card numbers. We comply with PCI-DSS standards to keep your financial information safe.',
    },
  ];

  const handleFAQPress = (id: number) => {
    setExpandedFAQ(expandedFAQ === id ? null : id);
  };

  const handleContactSupport = () => {
    if (!contactSubject.trim() || !contactMessage.trim()) {
      Alert.alert(t('support.requiredFields'), t('support.fillSubjectMessage'));
      return;
    }
    Alert.alert(
      'Message Sent',
      "Your support request has been submitted. We'll get back to you within 24 hours.",
      [{ text: 'OK', onPress: () => { setContactSubject(''); setContactMessage(''); } }]
    );
  };

  const handleEmailSupport = () => {
    Linking.openURL('mailto:support@workerconnect.com?subject=Support Request');
  };

  const handleCallSupport = () => {
    Linking.openURL('tel:+1234567890');
  };

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <StatusBar style={theme.statusBar} />
      <Header showBack title="Help & Support" />

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Quick Contact Options */}
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>{t('support.quickContact')}</Text>
          <View style={styles.contactButtons}>
            <TouchableOpacity style={[styles.contactButton, { backgroundColor: theme.surface }]} onPress={handleEmailSupport}>
              <Ionicons name="mail" size={32} color={theme.primary} />
              <Text style={[styles.contactButtonText, { color: theme.text }]}>{t('support.emailUs')}</Text>
              <Text style={[styles.contactButtonSubtext, { color: theme.textSecondary }]}>{t('support.supportEmail')}</Text>
            </TouchableOpacity>
            <TouchableOpacity style={[styles.contactButton, { backgroundColor: theme.surface }]} onPress={handleCallSupport}>
              <Ionicons name="call" size={32} color={theme.primary} />
              <Text style={[styles.contactButtonText, { color: theme.text }]}>{t('support.callUs')}</Text>
              <Text style={[styles.contactButtonSubtext, { color: theme.textSecondary }]}>{t('support.supportPhone')}</Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* FAQ Section */}
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>{t('help.faq')}</Text>
          <View style={[styles.faqContainer, { backgroundColor: theme.surface }]}>
            {faqs.map((faq, index) => (
              <View key={faq.id}>
                <TouchableOpacity style={styles.faqItem} onPress={() => handleFAQPress(faq.id)}>
                  <View style={styles.faqQuestion}>
                    <Ionicons name={expandedFAQ === faq.id ? 'remove-circle' : 'add-circle'} size={24} color={theme.primary} />
                    <Text style={[styles.faqQuestionText, { color: theme.text }]}>{faq.question}</Text>
                  </View>
                </TouchableOpacity>
                {expandedFAQ === faq.id && (
                  <View style={[styles.faqAnswer, { backgroundColor: theme.background }]}>
                    <Text style={[styles.faqAnswerText, { color: theme.textSecondary }]}>{faq.answer}</Text>
                  </View>
                )}
                {index < faqs.length - 1 && <View style={[styles.faqDivider, { backgroundColor: theme.border }]} />}
              </View>
            ))}
          </View>
        </View>

        {/* Contact Form */}
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>{t('support.sendMessage')}</Text>
          <View style={[styles.formCard, { backgroundColor: theme.surface }]}>
            <View style={styles.inputContainer}>
              <Text style={[styles.inputLabel, { color: theme.text }]}>{t('support.subject')}</Text>
              <TextInput
                style={[styles.input, { backgroundColor: theme.background, color: theme.text, borderColor: theme.border }]}
                placeholder={t('support.whatNeedHelp')}
                placeholderTextColor={theme.textSecondary}
                value={contactSubject}
                onChangeText={setContactSubject}
              />
            </View>
            <View style={styles.inputContainer}>
              <Text style={[styles.inputLabel, { color: theme.text }]}>{t('support.message')}</Text>
              <TextInput
                style={[styles.textArea, { backgroundColor: theme.background, color: theme.text, borderColor: theme.border }]}
                placeholder={t('support.describeIssue')}
                placeholderTextColor={theme.textSecondary}
                value={contactMessage}
                onChangeText={setContactMessage}
                multiline
                numberOfLines={6}
                textAlignVertical="top"
              />
            </View>
            <TouchableOpacity style={[styles.submitButton, { backgroundColor: theme.primary }]} onPress={handleContactSupport}>
              <Ionicons name="send" size={20} color="#FFFFFF" />
              <Text style={styles.submitButtonText}>{t('support.sendMessageButton')}</Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Help Articles */}
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>{t('support.helpArticles')}</Text>
          <View style={[styles.card, { backgroundColor: theme.surface }]}>
            {[
              { icon: 'book-outline', title: t('support.gettingStarted'), sub: t('support.learnBasics') },
              { icon: 'shield-checkmark-outline', title: t('support.safetySecurity'), sub: t('support.staySafe') },
              { icon: 'card-outline', title: 'Payments & Billing', sub: 'Learn about payment methods and billing' },
            ].map((item, idx, arr) => (
              <View key={idx}>
                <TouchableOpacity
                  style={styles.articleItem}
                  onPress={() => Alert.alert(t('profile.comingSoon'), t('support.articlesComingSoon'))}
                >
                  <Ionicons name={item.icon as any} size={24} color={theme.primary} />
                  <View style={styles.articleContent}>
                    <Text style={[styles.articleTitle, { color: theme.text }]}>{item.title}</Text>
                    <Text style={[styles.articleSubtitle, { color: theme.textSecondary }]}>{item.sub}</Text>
                  </View>
                  <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
                </TouchableOpacity>
                {idx < arr.length - 1 && <View style={[styles.divider, { backgroundColor: theme.border }]} />}
              </View>
            ))}
          </View>
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scrollContent: { padding: 16, paddingBottom: 40 },
  section: { marginBottom: 24 },
  sectionTitle: { fontSize: 20, fontFamily: 'Poppins_700Bold', marginBottom: 16 },
  contactButtons: { flexDirection: 'row', gap: 12 },
  contactButton: { flex: 1, alignItems: 'center', padding: 20, borderRadius: 16, shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.05, shadowRadius: 8, elevation: 2 },
  contactButtonText: { fontSize: 15, fontFamily: 'Poppins_600SemiBold', marginTop: 8 },
  contactButtonSubtext: { fontSize: 11, fontFamily: 'Poppins_400Regular', marginTop: 4, textAlign: 'center' },
  faqContainer: { borderRadius: 16, overflow: 'hidden', shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.05, shadowRadius: 8, elevation: 2 },
  faqItem: { padding: 16 },
  faqQuestion: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  faqQuestionText: { flex: 1, fontSize: 15, fontFamily: 'Poppins_600SemiBold' },
  faqAnswer: { padding: 16, paddingTop: 0 },
  faqAnswerText: { fontSize: 14, fontFamily: 'Poppins_400Regular', lineHeight: 22 },
  faqDivider: { height: 1, marginHorizontal: 16 },
  formCard: { borderRadius: 16, padding: 20, shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.05, shadowRadius: 8, elevation: 2 },
  inputContainer: { marginBottom: 20 },
  inputLabel: { fontSize: 14, fontFamily: 'Poppins_600SemiBold', marginBottom: 8 },
  input: { borderWidth: 1, borderRadius: 12, padding: 12, fontSize: 14, fontFamily: 'Poppins_400Regular' },
  textArea: { borderWidth: 1, borderRadius: 12, padding: 12, fontSize: 14, fontFamily: 'Poppins_400Regular', minHeight: 120 },
  submitButton: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, paddingVertical: 14, borderRadius: 12 },
  submitButtonText: { color: '#FFFFFF', fontSize: 16, fontFamily: 'Poppins_600SemiBold' },
  card: { borderRadius: 16, overflow: 'hidden', shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.05, shadowRadius: 8, elevation: 2 },
  articleItem: { flexDirection: 'row', alignItems: 'center', padding: 16, gap: 12 },
  articleContent: { flex: 1 },
  articleTitle: { fontSize: 15, fontFamily: 'Poppins_600SemiBold', marginBottom: 4 },
  articleSubtitle: { fontSize: 13, fontFamily: 'Poppins_400Regular' },
  divider: { height: 1, marginHorizontal: 16 },
});
