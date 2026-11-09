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
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../../components/Header';
import { useTranslation } from 'react-i18next';
import apiService from '../../services/api';

interface FAQ {
  id: number;
  question: string;
  answer: string;
}

export default function SupportScreen() {
  const { t } = useTranslation();
  const { theme, isDark } = useTheme();
  const [expandedFAQ, setExpandedFAQ] = useState<number | null>(null);
  const [contactSubject, setContactSubject] = useState('');
  const [contactMessage, setContactMessage] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const faqs: FAQ[] = [
    {
      id: 1,
      question: t('supportScreen.workerFaq1Q'),
      answer: t('supportScreen.workerFaq1A'),
    },
    {
      id: 2,
      question: t('supportScreen.workerFaq2Q'),
      answer: t('supportScreen.workerFaq2A'),
    },
    {
      id: 3,
      question: t('supportScreen.workerFaq3Q'),
      answer: t('supportScreen.workerFaq3A'),
    },
    {
      id: 4,
      question: t('supportScreen.workerFaq4Q'),
      answer: t('supportScreen.workerFaq4A'),
    },
    {
      id: 5,
      question: t('supportScreen.workerFaq5Q'),
      answer: t('supportScreen.workerFaq5A'),
    },
    {
      id: 6,
      question: t('supportScreen.workerFaq6Q'),
      answer: t('supportScreen.workerFaq6A'),
    },
    {
      id: 7,
      question: t('supportScreen.workerFaq7Q'),
      answer: t('supportScreen.workerFaq7A'),
    },
    {
      id: 8,
      question: t('supportScreen.workerFaq8Q'),
      answer: t('supportScreen.workerFaq8A'),
    },
  ];

  const handleFAQPress = (id: number) => {
    setExpandedFAQ(expandedFAQ === id ? null : id);
  };

  const handleContactSupport = async () => {
    if (!contactSubject.trim() || !contactMessage.trim()) {
      Alert.alert(t('support.requiredFields'), t('support.fillSubjectMessage'));
      return;
    }

    if (submitting) return;
    setSubmitting(true);
    try {
      await apiService.createSupportTicket({
        subject: contactSubject.trim(),
        description: contactMessage.trim(),
        category: 'other',
        priority: 'medium',
      });
      Alert.alert(
        t('supportScreen.messageSent'),
        t('support.messageSentSuccess'),
        [
          {
            text: t('common.ok'),
            onPress: () => {
              setContactSubject('');
              setContactMessage('');
            },
          },
        ]
      );
    } catch (error) {
      console.error('Error creating support ticket:', error);
      Alert.alert(
        t('common.error'),
        t('supportScreen.failedSubmit')
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handleEmailSupport = () => {
    Linking.openURL('mailto:sales@easyfix.co.tz?subject=Support Request');
  };

  const handleCallSupport = () => {
    // no public support line yet: support answers in Messages
    router.push('/(worker)/messages' as any);
  };

  const handleOpenTerms = () => router.push('/terms' as any);

  const handleOpenPrivacy = () => router.push('/terms?tab=privacy' as any);

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <StatusBar style={theme.statusBar} />
      <Header showBack title={t('help.helpSupport')} />

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Quick Contact Options */}
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>{t('support.quickContact')}</Text>
          
          <View style={styles.contactButtons}>
            <TouchableOpacity
              style={[styles.contactButton, { backgroundColor: theme.surface }]}
              onPress={handleEmailSupport}
            >
              <Ionicons name="mail" size={32} color={theme.primary} />
              <Text style={[styles.contactButtonText, { color: theme.text }]}>{t('support.emailUs')}</Text>
              <Text style={[styles.contactButtonSubtext, { color: theme.textSecondary }]}>{t('support.supportEmail')}</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[styles.contactButton, { backgroundColor: theme.surface }]}
              onPress={handleCallSupport}
            >
              <Ionicons name="chatbubbles" size={32} color={theme.primary} />
              <Text style={[styles.contactButtonText, { color: theme.text }]}>{t('messages.chatSupport')}</Text>
              <Text style={[styles.contactButtonSubtext, { color: theme.textSecondary }]}>{t('messages.supportReplies')}</Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* FAQ Section */}
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>{t('help.faq')}</Text>
          
          <View style={[styles.faqContainer, { backgroundColor: theme.surface }]}>
            {faqs.map((faq, index) => (
              <View key={faq.id}>
                <TouchableOpacity
                  style={styles.faqItem}
                  onPress={() => handleFAQPress(faq.id)}
                >
                  <View style={styles.faqQuestion}>
                    <Ionicons
                      name={expandedFAQ === faq.id ? 'remove-circle' : 'add-circle'}
                      size={24}
                      color={theme.primary}
                    />
                    <Text style={[styles.faqQuestionText, { color: theme.text }]}>
                      {faq.question}
                    </Text>
                  </View>
                </TouchableOpacity>
                
                {expandedFAQ === faq.id && (
                  <View style={[styles.faqAnswer, { backgroundColor: theme.background }]}>
                    <Text style={[styles.faqAnswerText, { color: theme.textSecondary }]}>
                      {faq.answer}
                    </Text>
                  </View>
                )}
                
                {index < faqs.length - 1 && (
                  <View style={[styles.faqDivider, { backgroundColor: theme.border }]} />
                )}
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

            <TouchableOpacity
              style={[styles.submitButton, { backgroundColor: theme.primary, opacity: submitting ? 0.7 : 1 }]}
              onPress={handleContactSupport}
              disabled={submitting}
            >
              <Ionicons name="send" size={20} color="#FFFFFF" />
              <Text style={styles.submitButtonText}>
                {submitting ? t('common.loading') : t('support.sendMessageButton')}
              </Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Help Articles */}
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>{t('support.helpArticles')}</Text>
          
          <View style={[styles.card, { backgroundColor: theme.surface }]}>
            <TouchableOpacity
              style={styles.articleItem}
              onPress={() => Alert.alert(t('profile.comingSoon'), t('support.articlesComingSoon'))}
            >
              <Ionicons name="book-outline" size={24} color={theme.primary} />
              <View style={styles.articleContent}>
                <Text style={[styles.articleTitle, { color: theme.text }]}>{t('support.gettingStarted')}</Text>
                <Text style={[styles.articleSubtitle, { color: theme.textSecondary }]}>{t('support.learnBasics')}</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
            </TouchableOpacity>

            <View style={[styles.divider, { backgroundColor: theme.border }]} />

            <TouchableOpacity
              style={styles.articleItem}
              onPress={() => Alert.alert(t('profile.comingSoon'), t('support.articlesComingSoon'))}
            >
              <Ionicons name="shield-checkmark-outline" size={24} color={theme.primary} />
              <View style={styles.articleContent}>
                <Text style={[styles.articleTitle, { color: theme.text }]}>{t('support.safetySecurity')}</Text>
                <Text style={[styles.articleSubtitle, { color: theme.textSecondary }]}>{t('support.staySafe')}</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
            </TouchableOpacity>

            <View style={[styles.divider, { backgroundColor: theme.border }]} />

            <TouchableOpacity
              style={styles.articleItem}
              onPress={() => Alert.alert(t('profile.comingSoon'), t('support.articlesComingSoon'))}
            >
              <Ionicons name="star-outline" size={24} color={theme.primary} />
              <View style={styles.articleContent}>
                <Text style={[styles.articleTitle, { color: theme.text }]}>{t('support.buildingProfile')}</Text>
                <Text style={[styles.articleSubtitle, { color: theme.textSecondary }]}>{t('support.attractClients')}</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
            </TouchableOpacity>
          </View>
        </View>

        {/* Legal Links */}
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>{t('support.legal')}</Text>
          
          <View style={[styles.card, { backgroundColor: theme.surface }]}>
            <TouchableOpacity
              style={styles.legalItem}
              onPress={handleOpenTerms}
            >
              <Ionicons name="document-text-outline" size={24} color={theme.primary} />
              <Text style={[styles.legalText, { color: theme.text }]}>{t('terms.termsOfService')}</Text>
              <Ionicons name="open-outline" size={20} color={theme.textSecondary} />
            </TouchableOpacity>

            <View style={[styles.divider, { backgroundColor: theme.border }]} />

            <TouchableOpacity
              style={styles.legalItem}
              onPress={handleOpenPrivacy}
            >
              <Ionicons name="lock-closed-outline" size={24} color={theme.primary} />
              <Text style={[styles.legalText, { color: theme.text }]}>{t('auth.privacyPolicy')}</Text>
              <Ionicons name="open-outline" size={20} color={theme.textSecondary} />
            </TouchableOpacity>
          </View>
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  scrollContent: {
    padding: 16,
    paddingBottom: 40,
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 20,
    fontFamily: 'Poppins_700Bold',
    marginBottom: 16,
  },
  contactButtons: {
    flexDirection: 'row',
    gap: 12,
  },
  contactButton: {
    flex: 1,
    alignItems: 'center',
    padding: 20,
    borderRadius: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  contactButtonText: {
    fontSize: 15,
    fontFamily: 'Poppins_600SemiBold',
    marginTop: 8,
  },
  contactButtonSubtext: {
    fontSize: 11,
    fontFamily: 'Poppins_400Regular',
    marginTop: 4,
    textAlign: 'center',
  },
  faqContainer: {
    borderRadius: 16,
    overflow: 'hidden',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  faqItem: {
    padding: 16,
  },
  faqQuestion: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  faqQuestionText: {
    flex: 1,
    fontSize: 15,
    fontFamily: 'Poppins_600SemiBold',
  },
  faqAnswer: {
    padding: 16,
    paddingTop: 0,
  },
  faqAnswerText: {
    fontSize: 14,
    fontFamily: 'Poppins_400Regular',
    lineHeight: 22,
  },
  faqDivider: {
    height: 1,
    marginHorizontal: 16,
  },
  formCard: {
    borderRadius: 16,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  inputContainer: {
    marginBottom: 20,
  },
  inputLabel: {
    fontSize: 14,
    fontFamily: 'Poppins_600SemiBold',
    marginBottom: 8,
  },
  input: {
    borderWidth: 1,
    borderRadius: 12,
    padding: 12,
    fontSize: 14,
    fontFamily: 'Poppins_400Regular',
  },
  textArea: {
    borderWidth: 1,
    borderRadius: 12,
    padding: 12,
    fontSize: 14,
    fontFamily: 'Poppins_400Regular',
    minHeight: 120,
  },
  submitButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 14,
    borderRadius: 12,
  },
  submitButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontFamily: 'Poppins_600SemiBold',
  },
  card: {
    borderRadius: 16,
    overflow: 'hidden',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  articleItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    gap: 12,
  },
  articleContent: {
    flex: 1,
  },
  articleTitle: {
    fontSize: 15,
    fontFamily: 'Poppins_600SemiBold',
    marginBottom: 4,
  },
  articleSubtitle: {
    fontSize: 13,
    fontFamily: 'Poppins_400Regular',
  },
  legalItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    gap: 12,
  },
  legalText: {
    flex: 1,
    fontSize: 15,
    fontFamily: 'Poppins_600SemiBold',
  },
  divider: {
    height: 1,
    marginHorizontal: 16,
  },
});
