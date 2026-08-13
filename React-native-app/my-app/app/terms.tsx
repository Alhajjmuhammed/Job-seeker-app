import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../contexts/ThemeContext';
import Header from '../components/Header';

// ─── Content Data ────────────────────────────────────────────────────────────

const TERMS_SECTIONS = [
  {
    number: '1',
    title: 'Introduction',
    body: 'Welcome to Worker Connect. These Terms and Conditions govern your use of our platform, website, and services. By accessing or using Worker Connect, you agree to be bound by these terms. If you disagree with any part of these terms, you may not access our service.',
  },
  {
    number: '2',
    title: 'Eligibility',
    body: 'To use Worker Connect, you must:',
    bullets: [
      'Be at least 18 years of age',
      'Have the legal capacity to enter into binding contracts',
      'Provide accurate and complete registration information',
      'Maintain the security of your account credentials',
      'For workers: Possess valid identification and required work permits in Tanzania',
    ],
  },
  {
    number: '3',
    title: 'User Accounts',
    body: 'Worker Connect offers three account types: Worker, Client, and Agent.',
    bullets: [
      'Workers: Must upload valid national ID, complete profile verification, and maintain accurate skill listings',
      'Clients: Must provide accurate company/personal information and payment details',
      'Agents: Must meet recruitment standards and comply with agent-specific terms',
    ],
    footer: 'You are responsible for maintaining the confidentiality of your account and password. You agree to notify us immediately of any unauthorized use of your account.',
  },
  {
    number: '4',
    title: 'Services',
    body: 'Worker Connect provides a platform connecting clients with verified workers. Our services include:',
    bullets: [
      'Job posting and worker matching',
      'Identity verification for workers',
      'Time tracking and progress monitoring',
      'Payment facilitation (where applicable)',
      'Review and rating systems',
      'Communication tools between parties',
    ],
  },
  {
    number: '5',
    title: 'Payment Terms',
    body: 'For Clients:',
    bullets: [
      'Payment terms are agreed upon during job posting',
      'Payments must be made according to the agreed schedule',
      'Platform fees may apply to transactions',
      'Refunds are subject to our refund policy and dispute resolution',
    ],
    subBody: 'For Workers:',
    subBullets: [
      'Workers receive payment according to job completion terms',
      'Accurate time tracking is mandatory',
      'Payment disputes must be reported within 7 days',
    ],
  },
  {
    number: '6',
    title: 'User Conduct',
    body: 'You agree NOT to:',
    bullets: [
      'Provide false, inaccurate, or misleading information',
      'Impersonate another person or entity',
      'Engage in fraudulent activities or scams',
      'Harass, abuse, or harm other users',
      'Violate any applicable laws or regulations',
      'Circumvent the platform for direct transactions',
      'Upload malicious content or viruses',
      'Scrape or copy platform content without permission',
    ],
  },
  {
    number: '7',
    title: 'Verification & Safety',
    body: 'Worker Connect conducts identity verification for all workers. However:',
    bullets: [
      'We cannot guarantee the complete accuracy of all user information',
      'Users are responsible for their own safety and due diligence',
      'We reserve the right to suspend accounts pending investigation',
      'Verified status does not constitute an endorsement or guarantee',
    ],
  },
  {
    number: '8',
    title: 'Intellectual Property',
    body: 'The Worker Connect platform, including its design, features, and content, is owned by Worker Connect and protected by copyright, trademark, and other intellectual property laws. You may not:',
    bullets: [
      'Copy, modify, or distribute platform content without permission',
      'Use our trademarks or branding without authorization',
      'Create derivative works based on our platform',
    ],
  },
  {
    number: '9',
    title: 'Limitation of Liability',
    body: 'Worker Connect acts as an intermediary platform. To the fullest extent permitted by law:',
    bullets: [
      'We are not liable for the quality, safety, or legality of services performed',
      'We do not guarantee job completion or worker availability',
      'We are not responsible for disputes between clients and workers',
      'Our liability is limited to the amount paid for platform services',
    ],
  },
  {
    number: '10',
    title: 'Dispute Resolution',
    body: 'In case of disputes:',
    bullets: [
      'Contact our support team within 7 days of the issue',
      'Provide all relevant documentation and evidence',
      'We will attempt to mediate and resolve disputes fairly',
      'Unresolved disputes may be subject to arbitration under Tanzanian law',
    ],
  },
  {
    number: '11',
    title: 'Modifications',
    body: 'We reserve the right to modify these terms at any time. Changes will be effective upon posting. Continued use of the platform after changes constitutes acceptance of the modified terms.',
  },
  {
    number: '12',
    title: 'Termination',
    body: 'We may terminate or suspend your account at any time for:',
    bullets: [
      'Violation of these terms',
      'Fraudulent or illegal activity',
      'Non-payment of fees',
      'Any reason at our discretion',
    ],
  },
];

const PRIVACY_SECTIONS = [
  {
    number: '1',
    title: 'Introduction',
    body: 'Worker Connect ("we," "us," or "our") is committed to protecting your privacy. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our platform and services.\n\nBy using Worker Connect, you agree to the collection and use of information in accordance with this policy.',
  },
  {
    number: '2',
    title: 'Information We Collect',
    body: 'We collect the following personal information:',
    bullets: [
      'Workers: Full name, national ID, phone, email, address, skills, experience, profile photo, and bank details',
      'Clients: Name, company name, phone, email, address, and payment information',
      'Agents: Name, phone, email, address, and commission details',
    ],
    subBody: 'Usage Information:',
    subBullets: [
      'Device information (IP address, browser type, operating system)',
      'Login dates and times',
      'Pages visited and features used',
      'Job searches and service requests',
      'Messages and communications within the platform',
    ],
    footer: 'We also collect location data for job matching, service delivery, and clock-in/clock-out tracking.',
  },
  {
    number: '3',
    title: 'How We Use Your Information',
    body: 'We use collected information to:',
    bullets: [
      'Create and maintain user accounts',
      'Verify worker identities and credentials',
      'Match clients with suitable workers',
      'Facilitate job assignments and service delivery',
      'Process payments and track earnings',
      'Send notifications about jobs, assignments, and updates',
      'Provide customer support',
      'Improve our services and user experience',
      'Prevent fraud and ensure platform security',
      'Comply with legal obligations',
    ],
  },
  {
    number: '4',
    title: 'Information Sharing',
    body: 'We share necessary information between clients and workers when a job match is made:',
    bullets: [
      'Workers can see client names, job details, and locations',
      'Clients can see worker profiles, skills, ratings, and availability',
      'Contact information is shared once a job is assigned',
    ],
    subBody: 'We may share information with third-party service providers for:',
    subBullets: [
      'Payment processing',
      'Cloud hosting and storage',
      'Email and SMS notifications',
      'Analytics and platform improvements',
    ],
    footer: 'We may also disclose information if required by law, court order, or government regulation.',
  },
  {
    number: '5',
    title: 'Data Security',
    body: 'We implement appropriate technical and organizational measures to protect your personal information:',
    bullets: [
      'Encryption of data in transit and at rest',
      'Secure authentication and access controls',
      'Regular security audits and updates',
      'Staff training on data protection',
      'Restricted access to personal information',
    ],
    footer: 'No method of transmission over the internet is 100% secure. While we strive to protect your information, we cannot guarantee absolute security.',
  },
  {
    number: '6',
    title: 'Your Rights',
    body: 'You have the right to:',
    bullets: [
      'Access: Request a copy of your personal information',
      'Correction: Update or correct inaccurate information',
      'Deletion: Request deletion of your account and personal data',
      'Objection: Object to processing of your information for certain purposes',
      'Portability: Request transfer of your data to another service',
      'Withdraw Consent: Withdraw consent for data processing where applicable',
    ],
    footer: 'To exercise these rights, please contact us at sales@easyfix.co.tz',
  },
  {
    number: '7',
    title: 'Data Retention',
    body: 'We retain your personal information for as long as necessary to:',
    bullets: [
      'Provide our services',
      'Comply with legal obligations',
      'Resolve disputes',
      'Enforce our agreements',
    ],
    footer: 'After account deletion, some information may be retained for legal, accounting, or backup purposes.',
  },
  {
    number: '8',
    title: 'Cookies and Tracking',
    body: 'We use cookies and similar tracking technologies to:',
    bullets: [
      'Remember your login sessions',
      'Understand user behavior and preferences',
      'Improve platform performance',
      'Provide personalized experiences',
    ],
    footer: 'You can control cookie settings through your browser, but disabling cookies may limit platform functionality.',
  },
  {
    number: '9',
    title: "Children's Privacy",
    body: "Worker Connect is not intended for users under 18 years of age. We do not knowingly collect information from children. If you become aware that a child has provided us with personal information, please contact us immediately.",
  },
  {
    number: '10',
    title: 'Changes to This Policy',
    body: 'We may update this Privacy Policy from time to time. Changes will be posted on this page with an updated revision date. We encourage you to review this policy periodically. Continued use of the platform after changes constitutes acceptance of the updated policy.',
  },
  {
    number: '11',
    title: 'International Data Transfers',
    body: 'Your information may be transferred to and processed in countries outside Tanzania. We ensure appropriate safeguards are in place to protect your information in accordance with this Privacy Policy.',
  },
];

// ─── Section Component ────────────────────────────────────────────────────────

type SectionData = {
  number: string;
  title: string;
  body?: string;
  bullets?: string[];
  subBody?: string;
  subBullets?: string[];
  footer?: string;
};

function Section({ section, accentColor, theme }: { section: SectionData; accentColor: string; theme: any }) {
  return (
    <View style={sectionStyles.container}>
      <View style={sectionStyles.headerRow}>
        <View style={[sectionStyles.numBadge, { backgroundColor: accentColor + '22' }]}>
          <Text style={[sectionStyles.numText, { color: accentColor }]}>{section.number}</Text>
        </View>
        <Text style={[sectionStyles.title, { color: theme.text }]}>{section.title}</Text>
      </View>
      {!!section.body && (
        <Text style={[sectionStyles.body, { color: theme.textSecondary }]}>{section.body}</Text>
      )}
      {section.bullets?.map((b, i) => (
        <View key={i} style={sectionStyles.bulletRow}>
          <View style={[sectionStyles.dot, { backgroundColor: accentColor }]} />
          <Text style={[sectionStyles.bulletText, { color: theme.textSecondary }]}>{b}</Text>
        </View>
      ))}
      {!!section.subBody && (
        <Text style={[sectionStyles.body, { color: theme.textSecondary, marginTop: 10 }]}>{section.subBody}</Text>
      )}
      {section.subBullets?.map((b, i) => (
        <View key={i} style={sectionStyles.bulletRow}>
          <View style={[sectionStyles.dot, { backgroundColor: accentColor }]} />
          <Text style={[sectionStyles.bulletText, { color: theme.textSecondary }]}>{b}</Text>
        </View>
      ))}
      {!!section.footer && (
        <Text style={[sectionStyles.footer, { color: theme.textSecondary }]}>{section.footer}</Text>
      )}
    </View>
  );
}

const sectionStyles = StyleSheet.create({
  container: { marginBottom: 20 },
  headerRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 10, gap: 10 },
  numBadge: { width: 32, height: 32, borderRadius: 16, alignItems: 'center', justifyContent: 'center' },
  numText: { fontSize: 13, fontFamily: 'Poppins_700Bold' },
  title: { fontSize: 16, fontFamily: 'Poppins_700Bold', flex: 1 },
  body: { fontSize: 14, lineHeight: 22, marginBottom: 6 },
  bulletRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 8, marginBottom: 5, paddingLeft: 4 },
  dot: { width: 6, height: 6, borderRadius: 3, marginTop: 8, flexShrink: 0 },
  bulletText: { fontSize: 14, lineHeight: 22, flex: 1 },
  footer: { fontSize: 13, lineHeight: 20, marginTop: 8, fontStyle: 'italic' },
});

// ─── Main Screen ──────────────────────────────────────────────────────────────

export default function TermsScreen() {
  const { theme, isDark } = useTheme();
  const [activeTab, setActiveTab] = useState<'terms' | 'privacy'>('terms');

  const isTerms = activeTab === 'terms';
  const accentColor = isTerms ? '#14b8a6' : '#10b981';
  const sections = isTerms ? TERMS_SECTIONS : PRIVACY_SECTIONS;

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <Header title="Terms & Privacy" showBack />

      {/* Tab Switcher */}
      <View style={[styles.tabBar, { backgroundColor: theme.surface, borderBottomColor: theme.border }]}>
        <TouchableOpacity
          style={[styles.tab, isTerms && [styles.tabActive, { borderBottomColor: '#14b8a6' }]]}
          onPress={() => setActiveTab('terms')}
        >
          <Ionicons name="document-text-outline" size={18} color={isTerms ? '#14b8a6' : theme.textSecondary} />
          <Text style={[styles.tabText, { color: isTerms ? '#14b8a6' : theme.textSecondary }]}>
            Terms & Conditions
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, !isTerms && [styles.tabActive, { borderBottomColor: '#10b981' }]]}
          onPress={() => setActiveTab('privacy')}
        >
          <Ionicons name="shield-checkmark-outline" size={18} color={!isTerms ? '#10b981' : theme.textSecondary} />
          <Text style={[styles.tabText, { color: !isTerms ? '#10b981' : theme.textSecondary }]}>
            Privacy Policy
          </Text>
        </TouchableOpacity>
      </View>

      <ScrollView style={styles.scroll} contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        {/* Hero */}
        <View style={[styles.hero, { backgroundColor: accentColor + (isDark ? '30' : '18') }]}>
          <View style={[styles.heroIcon, { backgroundColor: accentColor + '28' }]}>
            <Ionicons name={isTerms ? 'document-text' : 'shield-checkmark'} size={36} color={accentColor} />
          </View>
          <Text style={[styles.heroTitle, { color: theme.text }]}>
            {isTerms ? 'Terms & Conditions' : 'Privacy Policy'}
          </Text>
          <Text style={[styles.heroDate, { color: theme.textSecondary }]}>Last Updated: April 22, 2026</Text>
        </View>

        {/* Sections Card */}
        <View style={[styles.card, { backgroundColor: theme.surface }]}>
          {sections.map((s, idx) => (
            <View key={s.number}>
              <Section section={s} accentColor={accentColor} theme={theme} />
              {idx < sections.length - 1 && (
                <View style={[styles.divider, { backgroundColor: theme.border }]} />
              )}
            </View>
          ))}
        </View>

        {/* Contact Box */}
        <View style={[styles.contactBox, { backgroundColor: theme.surface, borderLeftColor: accentColor }]}>
          <Text style={[styles.contactTitle, { color: accentColor }]}>Contact Us</Text>
          <View style={styles.contactRow}>
            <Ionicons name="mail-outline" size={16} color={theme.textSecondary} />
            <Text style={[styles.contactText, { color: theme.textSecondary }]}>sales@easyfix.co.tz</Text>
          </View>
          <View style={styles.contactRow}>
            <Ionicons name="call-outline" size={16} color={theme.textSecondary} />
            <Text style={[styles.contactText, { color: theme.textSecondary }]}>+255 790 476 113</Text>
          </View>
          <View style={styles.contactRow}>
            <Ionicons name="location-outline" size={16} color={theme.textSecondary} />
            <Text style={[styles.contactText, { color: theme.textSecondary }]}>Fumba Road, Zanzibar, Tanzania</Text>
          </View>
        </View>

        {/* Footer Note */}
        <View style={[styles.footerNote, { backgroundColor: accentColor + '18', borderLeftColor: accentColor }]}>
          <Ionicons name={isTerms ? 'information-circle' : 'shield-checkmark'} size={18} color={accentColor} />
          <Text style={[styles.footerNoteText, { color: accentColor }]}>
            {isTerms
              ? 'By using Worker Connect, you acknowledge that you have read, understood, and agree to be bound by these Terms & Conditions.'
              : 'Your privacy matters to us. We are committed to protecting your personal information and using it responsibly.'}
          </Text>
        </View>

        <View style={{ height: 40 }} />
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  tabBar: {
    flexDirection: 'row',
    borderBottomWidth: 1,
  },
  tab: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    paddingVertical: 14,
    borderBottomWidth: 2,
    borderBottomColor: 'transparent',
  },
  tabActive: { borderBottomWidth: 2 },
  tabText: { fontSize: 13, fontFamily: 'Poppins_600SemiBold' },
  scroll: { flex: 1 },
  scrollContent: { padding: 16 },
  hero: {
    alignItems: 'center',
    paddingVertical: 28,
    borderRadius: 16,
    marginBottom: 16,
  },
  heroIcon: {
    width: 72,
    height: 72,
    borderRadius: 36,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 12,
  },
  heroTitle: { fontSize: 22, fontFamily: 'Poppins_700Bold', marginBottom: 4 },
  heroDate: { fontSize: 13 },
  card: {
    borderRadius: 16,
    padding: 20,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 8,
    elevation: 3,
  },
  divider: { height: 1, marginBottom: 20 },
  contactBox: {
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    borderLeftWidth: 4,
  },
  contactTitle: { fontSize: 15, fontFamily: 'Poppins_700Bold', marginBottom: 12 },
  contactRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 8 },
  contactText: { fontSize: 14 },
  footerNote: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 10,
    padding: 14,
    borderRadius: 10,
    borderLeftWidth: 4,
    marginBottom: 8,
  },
  footerNoteText: { fontSize: 13, lineHeight: 20, flex: 1, fontStyle: 'italic' },
});