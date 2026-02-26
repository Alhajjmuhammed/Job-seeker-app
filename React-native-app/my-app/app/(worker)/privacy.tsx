import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../../components/Header';
import apiService from '../../services/api';

export default function PrivacyScreen() {
  const { theme } = useTheme();
  const [privacyContent, setPrivacyContent] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadPrivacyContent();
  }, []);

  const loadPrivacyContent = async () => {
    try {
      const response = await apiService.getPrivacyPolicy();
      setPrivacyContent(response.content || 'Privacy policy not available.');
    } catch (error) {
      console.error('Error loading privacy policy:', error);
      Alert.alert('Error', 'Failed to load privacy policy');
      setPrivacyContent('Failed to load privacy policy. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <View style={[styles.container, styles.centered, { backgroundColor: theme.background }]}>
        <ActivityIndicator size="large" color={theme.primary} />
        <Text style={[styles.loadingText, { color: theme.text }]}>
          Loading privacy policy...
        </Text>
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <Header title="Privacy Policy" showBack />
      
      <ScrollView style={styles.scrollView} contentContainerStyle={styles.content}>
        <View style={[styles.contentContainer, { backgroundColor: theme.card }]}>
          <Text style={[styles.title, { color: theme.text }]}>
            Privacy Policy
          </Text>
          
          <Text style={[styles.lastUpdated, { color: theme.textSecondary }]}>
            Last updated: {new Date().toLocaleDateString()}
          </Text>
          
          <Text style={[styles.contentText, { color: theme.text }]}>
            {privacyContent}
          </Text>
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
  content: {
    padding: 16,
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
  },
  contentContainer: {
    padding: 20,
    borderRadius: 12,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 8,
    textAlign: 'center',
  },
  lastUpdated: {
    fontSize: 14,
    textAlign: 'center',
    marginBottom: 24,
  },
  contentText: {
    fontSize: 16,
    lineHeight: 24,
    textAlign: 'justify',
  },
});