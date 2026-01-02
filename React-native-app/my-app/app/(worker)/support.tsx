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

interface FAQ {
  id: number;
  question: string;
  answer: string;
}

export default function SupportScreen() {
  const { theme, isDark } = useTheme();
  const [expandedFAQ, setExpandedFAQ] = useState<number | null>(null);
  const [contactSubject, setContactSubject] = useState('');
  const [contactMessage, setContactMessage] = useState('');

  const faqs: FAQ[] = [
    {
      id: 1,
      question: 'How do I apply for jobs?',
      answer: 'Browse available jobs from the Jobs tab, tap on a job to view details, and click the "Apply Now" button. Fill in your cover letter and submit your application.',
    },
    {
      id: 2,
      question: 'How do I update my profile?',
      answer: 'Go to Profile tab, tap "Edit Profile" button, update your information, skills, and experience. Don\'t forget to upload your documents for verification.',
    },
    {
      id: 3,
      question: 'What are direct hire requests?',
      answer: 'Direct hire requests are job offers sent directly to you by clients who found your profile. You\'ll receive notifications when you get these requests on your Dashboard.',
    },
    {
      id: 4,
      question: 'How does the payment system work?',
      answer: 'Once you complete a job, the client marks it as complete and releases payment. You can view your earnings in the Earnings tab and request withdrawals to your linked bank account.',
    },
    {
      id: 5,
      question: 'How do I verify my documents?',
      answer: 'Upload your National ID and any professional certificates from the Documents section. Our admin team will review and verify them within 24-48 hours.',
    },
    {
      id: 6,
      question: 'Can I work for multiple clients?',
      answer: 'Yes! You can accept multiple jobs and work with different clients simultaneously. Just manage your availability status and schedule accordingly.',
    },
    {
      id: 7,
      question: 'What if I have a dispute with a client?',
      answer: 'Contact our support team immediately through this Help Center. We\'ll mediate the dispute and help resolve any issues between you and the client.',
    },
    {
      id: 8,
      question: 'How do I withdraw my earnings?',
      answer: 'Go to Earnings tab, ensure you have a linked payment method, and click "Withdraw Funds". Minimum withdrawal amount is $50. Funds typically arrive within 3-5 business days.',
    },
  ];

  const handleFAQPress = (id: number) => {
    setExpandedFAQ(expandedFAQ === id ? null : id);
  };

  const handleContactSupport = () => {
    if (!contactSubject.trim() || !contactMessage.trim()) {
      Alert.alert('Required Fields', 'Please fill in both subject and message');
      return;
    }

    // TODO: Implement actual API call to send support ticket
    Alert.alert(
      'Message Sent',
      'Your support request has been submitted. We\'ll get back to you within 24 hours.',
      [
        {
          text: 'OK',
          onPress: () => {
            setContactSubject('');
            setContactMessage('');
          },
        },
      ]
    );
  };

  const handleEmailSupport = () => {
    Linking.openURL('mailto:support@workerconnect.com?subject=Support Request');
  };

  const handleCallSupport = () => {
    Linking.openURL('tel:+1234567890');
  };

  const handleOpenTerms = () => {
    Alert.alert('Terms of Service', 'Terms of Service will open in a web view');
    // TODO: Implement WebView to show terms
  };

  const handleOpenPrivacy = () => {
    Alert.alert('Privacy Policy', 'Privacy Policy will open in a web view');
    // TODO: Implement WebView to show privacy policy
  };

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <StatusBar style={theme.statusBar} />
      <Header showBack title="Help & Support" />

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Quick Contact Options */}
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>Quick Contact</Text>
          
          <View style={styles.contactButtons}>
            <TouchableOpacity
              style={[styles.contactButton, { backgroundColor: theme.surface }]}
              onPress={handleEmailSupport}
            >
              <Ionicons name="mail" size={32} color={theme.primary} />
              <Text style={[styles.contactButtonText, { color: theme.text }]}>Email Us</Text>
              <Text style={[styles.contactButtonSubtext, { color: theme.textSecondary }]}>
                support@workerconnect.com
              </Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[styles.contactButton, { backgroundColor: theme.surface }]}
              onPress={handleCallSupport}
            >
              <Ionicons name="call" size={32} color={theme.primary} />
              <Text style={[styles.contactButtonText, { color: theme.text }]}>Call Us</Text>
              <Text style={[styles.contactButtonSubtext, { color: theme.textSecondary }]}>
                +1 (234) 567-890
              </Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* FAQ Section */}
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>
            Frequently Asked Questions
          </Text>
          
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
          <Text style={[styles.sectionTitle, { color: theme.text }]}>Send Us a Message</Text>
          
          <View style={[styles.formCard, { backgroundColor: theme.surface }]}>
            <View style={styles.inputContainer}>
              <Text style={[styles.inputLabel, { color: theme.text }]}>Subject</Text>
              <TextInput
                style={[styles.input, { backgroundColor: theme.background, color: theme.text, borderColor: theme.border }]}
                placeholder="What do you need help with?"
                placeholderTextColor={theme.textSecondary}
                value={contactSubject}
                onChangeText={setContactSubject}
              />
            </View>

            <View style={styles.inputContainer}>
              <Text style={[styles.inputLabel, { color: theme.text }]}>Message</Text>
              <TextInput
                style={[styles.textArea, { backgroundColor: theme.background, color: theme.text, borderColor: theme.border }]}
                placeholder="Describe your issue or question..."
                placeholderTextColor={theme.textSecondary}
                value={contactMessage}
                onChangeText={setContactMessage}
                multiline
                numberOfLines={6}
                textAlignVertical="top"
              />
            </View>

            <TouchableOpacity
              style={[styles.submitButton, { backgroundColor: theme.primary }]}
              onPress={handleContactSupport}
            >
              <Ionicons name="send" size={20} color="#FFFFFF" />
              <Text style={styles.submitButtonText}>Send Message</Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Help Articles */}
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>Help Articles</Text>
          
          <View style={[styles.card, { backgroundColor: theme.surface }]}>
            <TouchableOpacity
              style={styles.articleItem}
              onPress={() => Alert.alert('Coming Soon', 'Help articles coming soon')}
            >
              <Ionicons name="book-outline" size={24} color={theme.primary} />
              <View style={styles.articleContent}>
                <Text style={[styles.articleTitle, { color: theme.text }]}>
                  Getting Started Guide
                </Text>
                <Text style={[styles.articleSubtitle, { color: theme.textSecondary }]}>
                  Learn the basics of WorkerConnect
                </Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
            </TouchableOpacity>

            <View style={[styles.divider, { backgroundColor: theme.border }]} />

            <TouchableOpacity
              style={styles.articleItem}
              onPress={() => Alert.alert('Coming Soon', 'Help articles coming soon')}
            >
              <Ionicons name="shield-checkmark-outline" size={24} color={theme.primary} />
              <View style={styles.articleContent}>
                <Text style={[styles.articleTitle, { color: theme.text }]}>
                  Safety & Security Tips
                </Text>
                <Text style={[styles.articleSubtitle, { color: theme.textSecondary }]}>
                  Stay safe while working
                </Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
            </TouchableOpacity>

            <View style={[styles.divider, { backgroundColor: theme.border }]} />

            <TouchableOpacity
              style={styles.articleItem}
              onPress={() => Alert.alert('Coming Soon', 'Help articles coming soon')}
            >
              <Ionicons name="star-outline" size={24} color={theme.primary} />
              <View style={styles.articleContent}>
                <Text style={[styles.articleTitle, { color: theme.text }]}>
                  Building Your Profile
                </Text>
                <Text style={[styles.articleSubtitle, { color: theme.textSecondary }]}>
                  Tips for attracting clients
                </Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
            </TouchableOpacity>
          </View>
        </View>

        {/* Legal Links */}
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>Legal</Text>
          
          <View style={[styles.card, { backgroundColor: theme.surface }]}>
            <TouchableOpacity
              style={styles.legalItem}
              onPress={handleOpenTerms}
            >
              <Ionicons name="document-text-outline" size={24} color={theme.primary} />
              <Text style={[styles.legalText, { color: theme.text }]}>Terms of Service</Text>
              <Ionicons name="open-outline" size={20} color={theme.textSecondary} />
            </TouchableOpacity>

            <View style={[styles.divider, { backgroundColor: theme.border }]} />

            <TouchableOpacity
              style={styles.legalItem}
              onPress={handleOpenPrivacy}
            >
              <Ionicons name="lock-closed-outline" size={24} color={theme.primary} />
              <Text style={[styles.legalText, { color: theme.text }]}>Privacy Policy</Text>
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
