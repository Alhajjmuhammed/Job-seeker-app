import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  RefreshControl,
  ActivityIndicator,
  Alert,
  Linking,
} from 'react-native';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../../components/Header';
import apiService from '../../services/api';
import { useTranslation } from 'react-i18next';

interface FAQ {
  id: number;
  question: string;
  answer: string;
  category: string;
}

interface ContactInfo {
  email: string;
  phone: string;
  address: string;
  business_hours: string;
  support_hours: string;
}

export default function HelpScreen() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { theme } = useTheme();
  const [faqs, setFaqs] = useState<Record<string, FAQ[]>>({});
  const [contactInfo, setContactInfo] = useState<ContactInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<string>('general');
  const [expandedFaq, setExpandedFaq] = useState<number | null>(null);

  const categories = [
    { value: 'general', label: 'General', icon: 'help-circle' as const },
    { value: 'worker', label: 'For Workers', icon: 'hammer' as const },
    { value: 'client', label: 'For Clients', icon: 'briefcase' as const },
    { value: 'payment', label: 'Payments', icon: 'card' as const },
    { value: 'technical', label: 'Technical', icon: 'settings' as const },
  ];

  useEffect(() => {
    loadFAQs();
    loadContactInfo();
  }, []);

  const loadFAQs = async () => {
    try {
      const response = await apiService.getFAQ();
      if (response.success) {
        setFaqs(response.faqs_by_category || {});
      }
    } catch (error) {
      console.error('Error loading FAQs:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const loadContactInfo = async () => {
    try {
      const response = await apiService.getContactInfo();
      setContactInfo(response);
    } catch (error) {
      console.error('Error loading contact info:', error);
    }
  };

  const onRefresh = () => {
    setRefreshing(true);
    loadFAQs();
    loadContactInfo();
  };

  const handleContact = (method: 'email' | 'phone') => {
    if (!contactInfo) return;

    if (method === 'email') {
      Linking.openURL(`mailto:${contactInfo.email}`);
    } else if (method === 'phone') {
      Linking.openURL(`tel:${contactInfo.phone}`);
    }
  };

  const handleCreateTicket = () => {
    router.push('/(worker)/support');
  };

  const renderFAQItem = (faq: FAQ) => (
    <TouchableOpacity
      key={faq.id}
      style={[
        styles.faqItem,
        { 
          backgroundColor: theme.card,
          borderBottomColor: theme.border
        }
      ]}
      onPress={() => setExpandedFaq(expandedFaq === faq.id ? null : faq.id)}
    >
      <View style={styles.faqHeader}>
        <Text style={[styles.faqQuestion, { color: theme.text }]}>
          {faq.question}
        </Text>
        <Ionicons
          name={expandedFaq === faq.id ? 'chevron-up' : 'chevron-down'}
          size={20}
          color={theme.textSecondary}
        />
      </View>
      {expandedFaq === faq.id && (
        <Text style={[styles.faqAnswer, { color: theme.textSecondary }]}>
          {faq.answer}
        </Text>
      )}
    </TouchableOpacity>
  );

  if (loading) {
    return (
      <View style={[styles.container, styles.centered, { backgroundColor: theme.background }]}>
        <ActivityIndicator size="large" color={theme.primary} />
        <Text style={[styles.loadingText, { color: theme.text }]}>{t('help.loadingHelp')}</Text>
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <Header title="Help & Support" showBack />
      
      <ScrollView
        style={styles.scrollView}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            colors={[theme.primary]}
          />
        }
      >
        {/* Quick Actions */}
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>{t('help.needImmediateHelp')}</Text>
          
          <TouchableOpacity
            style={[styles.actionButton, { backgroundColor: theme.primary }]}
            onPress={handleCreateTicket}
          >
            <Ionicons name="chatbubble-ellipses" size={24} color="white" />
            <Text style={styles.actionButtonText}>{t('help.createSupportTicket')}</Text>
          </TouchableOpacity>

          {contactInfo && (
            <View style={styles.contactButtons}>
              <TouchableOpacity
                style={[
                  styles.contactButton,
                  { backgroundColor: theme.card, borderColor: theme.border }
                ]}
                onPress={() => handleContact('email')}
              >
                <Ionicons name="mail" size={20} color={theme.primary} />
                <Text style={[styles.contactButtonText, { color: theme.text }]}>{t('help.emailSupport')}</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[
                  styles.contactButton,
                  { backgroundColor: theme.card, borderColor: theme.border }
                ]}
                onPress={() => handleContact('phone')}
              >
                <Ionicons name="call" size={20} color={theme.primary} />
                <Text style={[styles.contactButtonText, { color: theme.text }]}>{t('help.callSupport')}</Text>
              </TouchableOpacity>
            </View>
          )}
        </View>

        {/* Contact Information */}
        {contactInfo && (
          <View style={[styles.section, styles.contactSection, { backgroundColor: theme.card }]}>
            <Text style={[styles.sectionTitle, { color: theme.text }]}>{t('help.contactInformation')}</Text>
            
            <View style={styles.contactInfo}>
              <View style={styles.contactRow}>
                <Ionicons name="mail" size={16} color={theme.textSecondary} />
                <Text style={[styles.contactText, { color: theme.textSecondary }]}>
                  {contactInfo.email}
                </Text>
              </View>
              
              <View style={styles.contactRow}>
                <Ionicons name="call" size={16} color={theme.textSecondary} />
                <Text style={[styles.contactText, { color: theme.textSecondary }]}>
                  {contactInfo.phone}
                </Text>
              </View>
              
              <View style={styles.contactRow}>
                <Ionicons name="time" size={16} color={theme.textSecondary} />
                <Text style={[styles.contactText, { color: theme.textSecondary }]}>
                  {contactInfo.business_hours}
                </Text>
              </View>
              
              <View style={styles.contactRow}>
                <Ionicons name="shield-checkmark" size={16} color={theme.textSecondary} />
                <Text style={[styles.contactText, { color: theme.textSecondary }]}>
                  Emergency: {contactInfo.support_hours}
                </Text>
              </View>
            </View>
          </View>
        )}

        {/* FAQ Categories */}
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>{t('help.faq')}</Text>
          
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            style={styles.categoryScroll}
            contentContainerStyle={styles.categoryScrollContent}
          >
            {categories.map((category) => (
              <TouchableOpacity
                key={category.value}
                style={[
                  styles.categoryButton,
                  {
                    backgroundColor: selectedCategory === category.value
                      ? theme.primary
                      : theme.card,
                    borderColor: theme.border,
                  }
                ]}
                onPress={() => setSelectedCategory(category.value)}
              >
                <Ionicons
                  name={category.icon}
                  size={20}
                  color={selectedCategory === category.value ? 'white' : theme.textSecondary}
                />
                <Text
                  style={[
                    styles.categoryButtonText,
                    {
                      color: selectedCategory === category.value ? 'white' : theme.text,
                    }
                  ]}
                >
                  {category.label}
                </Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        </View>

        {/* FAQ Items */}
        <View style={styles.section}>
          {faqs[selectedCategory]?.length > 0 ? (
            <View style={[styles.faqContainer, { backgroundColor: theme.card }]}>
              {faqs[selectedCategory].map(renderFAQItem)}
            </View>
          ) : (
            <View style={[styles.emptyContainer, styles.centered]}>
              <Ionicons name="help-circle-outline" size={64} color={theme.textSecondary} />
              <Text style={[styles.emptyTitle, { color: theme.text }]}>{t('help.noFAQs')}</Text>
              <Text style={[styles.emptySubtitle, { color: theme.textSecondary }]}>{t('help.addingContent')}</Text>
            </View>
          )}
        </View>

        {/* Additional Resources */}
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>{t('help.additionalResources')}</Text>
          
          <TouchableOpacity
            style={[styles.resourceButton, { backgroundColor: theme.card, borderColor: theme.border }]}
            onPress={() => router.push('/(worker)/terms')}
          >
            <Ionicons name="document-text" size={24} color={theme.primary} />
            <View style={styles.resourceText}>
              <Text style={[styles.resourceTitle, { color: theme.text }]}>{t('terms.termsOfService')}</Text>
              <Text style={[styles.resourceSubtitle, { color: theme.textSecondary }]}>{t('help.readTerms')}</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.resourceButton, { backgroundColor: theme.card, borderColor: theme.border }]}
            onPress={() => router.push('/(worker)/privacy')}
          >
            <Ionicons name="shield-checkmark" size={24} color={theme.primary} />
            <View style={styles.resourceText}>
              <Text style={[styles.resourceTitle, { color: theme.text }]}>{t('auth.privacyPolicy')}</Text>
              <Text style={[styles.resourceSubtitle, { color: theme.textSecondary }]}>{t('help.learnPrivacy')}</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color={theme.textSecondary} />
          </TouchableOpacity>
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  centered: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  scrollView: {
    flex: 1,
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
  },
  section: {
    padding: 16,
  },
  contactSection: {
    marginHorizontal: 16,
    marginBottom: 16,
    borderRadius: 12,
    padding: 16,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 16,
  },
  actionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    borderRadius: 12,
    marginBottom: 16,
    gap: 8,
  },
  actionButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  contactButtons: {
    flexDirection: 'row',
    gap: 12,
  },
  contactButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 12,
    borderRadius: 8,
    borderWidth: 1,
    gap: 8,
  },
  contactButtonText: {
    fontSize: 14,
    fontWeight: '500',
  },
  contactInfo: {
    gap: 12,
  },
  contactRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  contactText: {
    fontSize: 14,
  },
  categoryScroll: {
    marginBottom: 16,
  },
  categoryScrollContent: {
    paddingHorizontal: 4,
    gap: 8,
  },
  categoryButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    borderWidth: 1,
    gap: 6,
  },
  categoryButtonText: {
    fontSize: 14,
    fontWeight: '500',
  },
  faqContainer: {
    borderRadius: 12,
    overflow: 'hidden',
  },
  faqItem: {
    padding: 16,
    borderBottomWidth: 1,
  },
  faqHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  faqQuestion: {
    flex: 1,
    fontSize: 16,
    fontWeight: '500',
    marginRight: 8,
  },
  faqAnswer: {
    marginTop: 12,
    fontSize: 14,
    lineHeight: 20,
  },
  emptyContainer: {
    padding: 48,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginTop: 16,
    textAlign: 'center',
  },
  emptySubtitle: {
    fontSize: 14,
    marginTop: 8,
    textAlign: 'center',
  },
  resourceButton: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    marginBottom: 12,
    gap: 12,
  },
  resourceText: {
    flex: 1,
  },
  resourceTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 4,
  },
  resourceSubtitle: {
    fontSize: 14,
  },
});