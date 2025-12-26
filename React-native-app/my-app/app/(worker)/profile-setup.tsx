import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import * as DocumentPicker from 'expo-document-picker';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import apiService from '../../services/api';
import Header from '../../components/Header';

type SetupStep = 'welcome' | 'documents' | 'skills' | 'complete';

export default function ProfileSetupScreen() {
  const [currentStep, setCurrentStep] = useState<SetupStep>('welcome');
  const [hasUploadedID, setHasUploadedID] = useState(false);
  const [optionalDocsCount, setOptionalDocsCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [completion, setCompletion] = useState(20);
  const { user } = useAuth();
  const { theme, isDark } = useTheme();

  // Fetch current profile completion on mount
  useEffect(() => {
    fetchProfileCompletion();
  }, []);

  const fetchProfileCompletion = async () => {
    try {
      const data = await apiService.getProfileCompletion();
      setCompletion(data.profile_completion_percentage);
      setHasUploadedID(data.has_uploaded_national_id);
    } catch (error) {
      console.error('Failed to fetch profile completion:', error);
    }
  };

  const canProceed = hasUploadedID; // Can only proceed if National ID is uploaded

  const handleSkipToDocuments = () => {
    setCurrentStep('documents');
  };

  const handleDocumentUpload = async (documentType: 'id' | 'cv' | 'certificate' | 'license' | 'other') => {
    try {
      // Pick document
      const result = await DocumentPicker.getDocumentAsync({
        type: ['image/*', 'application/pdf'],
        copyToCacheDirectory: true,
      });

      if (result.canceled) {
        return;
      }

      const file = result.assets[0];
      setLoading(true);

      // Prepare file for upload
      const fileToUpload: any = {
        uri: file.uri,
        type: file.mimeType || 'application/octet-stream',
        name: file.name,
      };

      // Upload to backend
      const response = await apiService.uploadDocument(fileToUpload, documentType);
      
      // Update state based on response
      setCompletion(response.profile_completion_percentage);
      setHasUploadedID(response.has_uploaded_national_id);
      
      if (documentType === 'id') {
        Alert.alert('Success', 'National ID uploaded! You can now proceed or add more documents.');
      } else {
        setOptionalDocsCount(prev => prev + 1);
        Alert.alert('Success', 'Document uploaded successfully!');
      }
    } catch (error: any) {
      console.error('Document upload failed:', error);
      Alert.alert('Upload Failed', error.response?.data?.error || 'Failed to upload document. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleContinueToSkills = () => {
    if (!canProceed) {
      Alert.alert('Required', 'Please upload your National ID first to continue.');
      return;
    }
    setCurrentStep('skills');
  };

  const handleFinishSetup = () => {
    if (!canProceed) {
      Alert.alert('Required', 'Please upload your National ID to finish setup.');
      return;
    }
    
    // Mark profile as complete and navigate to dashboard
    Alert.alert(
      'Profile Setup Complete!',
      `Your profile is ${completion}% complete. ${completion === 100 ? 'Great job!' : 'You can add more details later in your profile.'}`,
      [
        {
          text: 'Go to Dashboard',
          onPress: () => router.replace('/(worker)/dashboard'),
        },
      ]
    );
  };

  const handleSkipForNow = () => {
    if (!canProceed) {
      Alert.alert(
        'National ID Required',
        'You must upload your National ID before you can skip. This is mandatory for verification.',
        [{ text: 'OK' }]
      );
      return;
    }
    
    Alert.alert(
      'Skip Setup?',
      `Your profile is ${completion}% complete. You can complete it later from your profile page.`,
      [
        { text: 'Continue Setup', style: 'cancel' },
        {
          text: 'Skip',
          style: 'destructive',
          onPress: () => router.replace('/(worker)/dashboard'),
        },
      ]
    );
  };

  const renderWelcomeStep = () => (
    <View style={styles.stepContainer}>
      <View style={styles.welcomeIcon}>
        <Ionicons name="checkmark-done-circle" size={80} color={theme.primary} />
      </View>
      <Text style={styles.welcomeTitle}>Welcome, {user?.firstName}!</Text>
      <Text style={styles.welcomeSubtitle}>
        Let's set up your profile to start receiving job requests from clients
      </Text>

      <View style={styles.setupSteps}>
        <View style={styles.setupStepItem}>
          <View style={styles.stepNumber}>
            <Text style={styles.stepNumberText}>1</Text>
          </View>
          <View style={styles.stepContent}>
            <Text style={styles.stepTitle}>Upload National ID</Text>
            <Text style={styles.stepDescription}>Required for verification (mandatory)</Text>
          </View>
        </View>

        <View style={styles.setupStepItem}>
          <View style={styles.stepNumber}>
            <Text style={styles.stepNumberText}>2</Text>
          </View>
          <View style={styles.stepContent}>
            <Text style={styles.stepTitle}>Add Optional Documents</Text>
            <Text style={styles.stepDescription}>Certificates, degrees, or experience proof</Text>
          </View>
        </View>

        <View style={styles.setupStepItem}>
          <View style={styles.stepNumber}>
            <Text style={styles.stepNumberText}>3</Text>
          </View>
          <View style={styles.stepContent}>
            <Text style={styles.stepTitle}>Set Skills & Availability</Text>
            <Text style={styles.stepDescription}>Help clients find you easily</Text>
          </View>
        </View>
      </View>

      <TouchableOpacity
        style={styles.primaryButton}
        onPress={handleSkipToDocuments}
      >
        <Text style={styles.primaryButtonText}>Get Started</Text>
        <Ionicons name="arrow-forward" size={20} color="#FFF" />
      </TouchableOpacity>
    </View>
  );

  const renderDocumentsStep = () => (
    <View style={styles.stepContainer}>
      <Text style={styles.stepTitle}>Upload Documents</Text>
      <Text style={styles.stepSubtitle}>
        Upload your National ID first (required), then add optional documents
      </Text>

      {/* Progress Indicator */}
      <View style={styles.progressCard}>
        <View style={styles.progressHeader}>
          <Text style={styles.progressLabel}>Profile Completion</Text>
          <Text style={styles.progressPercentage}>{completion}%</Text>
        </View>
        <View style={styles.progressBarContainer}>
          <View style={[styles.progressBar, { width: `${completion}%` }]} />
        </View>
        <View style={styles.progressHintContainer}>
          {!hasUploadedID ? (
            <>
              <Ionicons name="alert-circle" size={16} color={theme.error} />
              <Text style={styles.progressHint}>Upload National ID to proceed</Text>
            </>
          ) : completion === 100 ? (
            <>
              <Ionicons name="checkmark-circle" size={16} color={theme.success} />
              <Text style={styles.progressHint}>Profile complete!</Text>
            </>
          ) : (
            <>
              <Ionicons name="ellipse-outline" size={16} color={theme.textSecondary} />
              <Text style={styles.progressHint}>Add more documents for 100%</Text>
            </>
          )}
        </View>
      </View>

      {/* National ID Upload */}
      <View style={styles.documentSection}>
        <View style={styles.documentSectionTitleContainer}>
          <Ionicons name="alert-circle" size={20} color={theme.error} />
          <Text style={styles.documentSectionTitle}>Required Document</Text>
        </View>
        <TouchableOpacity
          style={[
            styles.uploadCard,
            hasUploadedID && styles.uploadCardComplete,
          ]}
          onPress={() => {
            if (!hasUploadedID) {
              handleDocumentUpload('id');
            }
          }}
          disabled={loading || hasUploadedID}
        >
          {loading && !hasUploadedID ? (
            <ActivityIndicator size="large" color={theme.primary} />
          ) : (
            <Ionicons
              name={hasUploadedID ? 'checkmark-circle' : 'cloud-upload-outline'}
              size={32}
              color={hasUploadedID ? theme.success : theme.primary}
            />
          )}
          <Text style={styles.uploadCardTitle}>National ID</Text>
          <Text style={styles.uploadCardStatus}>
            {hasUploadedID ? 'Uploaded' : 'Tap to upload'}
          </Text>
        </TouchableOpacity>
      </View>

      {/* Optional Documents */}
      <View style={styles.documentSection}>
        <View style={styles.documentSectionTitleContainer}>
          <Ionicons name="ellipse-outline" size={20} color={theme.textSecondary} />
          <Text style={styles.documentSectionTitle}>Optional Documents (Recommended)</Text>
        </View>
        <View style={styles.optionalDocsGrid}>
          <TouchableOpacity
            style={styles.uploadCard}
            onPress={() => handleDocumentUpload('certificate')}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator size="small" color={theme.primary} />
            ) : (
              <Ionicons name="school-outline" size={32} color={theme.primary} />
            )}
            <Text style={styles.uploadCardTitle}>Certificates</Text>
            <Text style={styles.uploadCardStatus}>Tap to upload</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.uploadCard}
            onPress={() => handleDocumentUpload('cv')}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator size="small" color={theme.primary} />
            ) : (
              <Ionicons name="briefcase-outline" size={32} color={theme.primary} />
            )}
            <Text style={styles.uploadCardTitle}>CV/Resume</Text>
            <Text style={styles.uploadCardStatus}>Tap to upload</Text>
          </TouchableOpacity>
        </View>
      </View>

      <View style={styles.buttonGroup}>
        <TouchableOpacity
          style={[styles.secondaryButton, !canProceed && styles.buttonDisabled]}
          onPress={handleContinueToSkills}
          disabled={!canProceed}
        >
          <Text style={styles.secondaryButtonText}>Continue</Text>
          <Ionicons name="arrow-forward" size={20} color={canProceed ? theme.primary : theme.textSecondary} />
        </TouchableOpacity>

        {canProceed && (
          <TouchableOpacity
            style={styles.linkButton}
            onPress={handleSkipForNow}
          >
            <Text style={styles.linkButtonText}>Skip for now</Text>
          </TouchableOpacity>
        )}
      </View>
    </View>
  );

  const renderSkillsStep = () => (
    <View style={styles.stepContainer}>
      <Text style={styles.stepTitle}>Almost Done!</Text>
      <Text style={styles.stepSubtitle}>
        Add skills and set your availability
      </Text>

      <View style={styles.infoCard}>
        <Ionicons name="information-circle" size={24} color={theme.primary} />
        <Text style={styles.infoText}>
          You can add more details later from your profile page
        </Text>
      </View>

      <TouchableOpacity
        style={styles.primaryButton}
        onPress={handleFinishSetup}
      >
        <Ionicons name="checkmark-circle" size={20} color="#FFF" />
        <Text style={styles.primaryButtonText}>Finish Setup</Text>
      </TouchableOpacity>

      <TouchableOpacity
        style={styles.linkButton}
        onPress={handleSkipForNow}
      >
        <Text style={styles.linkButtonText}>Skip and go to dashboard</Text>
      </TouchableOpacity>
    </View>
  );

  const styles = StyleSheet.create({
    container: {
      flex: 1,
      backgroundColor: theme.background,
    },
    stepIndicatorContainer: {
      flexDirection: 'row',
      justifyContent: 'center',
      gap: 8,
      paddingHorizontal: 20,
      paddingVertical: 12,
    },
    stepDot: {
      width: 8,
      height: 8,
      borderRadius: 4,
      backgroundColor: isDark ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.2)',
    },
    stepDotActive: {
      backgroundColor: theme.primary,
    },
    scrollContent: {
      padding: 20,
    },
    stepContainer: {
      flex: 1,
    },
    welcomeIcon: {
      alignItems: 'center',
      marginBottom: 20,
    },
    welcomeTitle: {
      fontSize: 28,
      fontFamily: theme.fontBold,
      color: theme.text,
      textAlign: 'center',
      marginBottom: 12,
    },
    welcomeSubtitle: {
      fontSize: 16,
      color: theme.textSecondary,
      textAlign: 'center',
      marginBottom: 40,
      lineHeight: 24,
    },
    setupSteps: {
      marginBottom: 40,
    },
    setupStepItem: {
      flexDirection: 'row',
      marginBottom: 24,
    },
    stepNumber: {
      width: 40,
      height: 40,
      borderRadius: 20,
      backgroundColor: theme.primary,
      alignItems: 'center',
      justifyContent: 'center',
      marginRight: 16,
    },
    stepNumberText: {
      color: '#FFFFFF',
      fontSize: 18,
      fontFamily: theme.fontBold,
    },
    stepContent: {
      flex: 1,
    },
    stepTitle: {
      fontSize: 18,
      fontFamily: theme.fontSemiBold,
      color: theme.text,
      marginBottom: 16,
    },
    stepDescription: {
      fontSize: 14,
      color: theme.textSecondary,
      lineHeight: 20,
    },
    stepSubtitle: {
      fontSize: 14,
      color: theme.textSecondary,
      marginBottom: 24,
    },
    progressCard: {
      backgroundColor: theme.surface,
      borderRadius: 12,
      padding: 20,
      marginBottom: 24,
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: isDark ? 0.3 : 0.1,
      shadowRadius: 4,
      elevation: 3,
    },
    progressHeader: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      marginBottom: 12,
    },
    progressLabel: {
      fontSize: 16,
      fontFamily: theme.fontSemiBold,
      color: theme.text,
    },
    progressPercentage: {
      fontSize: 18,
      fontFamily: theme.fontBold,
      color: theme.primary,
    },
    progressBarContainer: {
      height: 8,
      backgroundColor: isDark ? '#374151' : '#E5E7EB',
      borderRadius: 4,
      overflow: 'hidden',
      marginBottom: 12,
    },
    progressBar: {
      height: '100%',
      backgroundColor: theme.primary,
      borderRadius: 4,
    },
    progressHintContainer: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 8,
    },
    progressHint: {
      fontSize: 14,
      color: theme.textSecondary,
      textAlign: 'center',
    },
    documentSection: {
      marginBottom: 24,
    },
    documentSectionTitleContainer: {
      flexDirection: 'row',
      alignItems: 'center',
      gap: 8,
      marginBottom: 12,
    },
    documentSectionTitle: {
      fontSize: 16,
      fontFamily: theme.fontSemiBold,
      color: theme.text,
    },
    uploadCard: {
      backgroundColor: theme.surface,
      borderRadius: 12,
      padding: 20,
      alignItems: 'center',
      borderWidth: 2,
      borderColor: isDark ? '#4B5563' : '#E5E7EB',
      borderStyle: 'dashed',
    },
    uploadCardComplete: {
      borderColor: '#4CAF50',
      borderStyle: 'solid',
      backgroundColor: isDark ? '#065f46' : '#F0F9FF',
    },
    uploadCardTitle: {
      fontSize: 16,
      fontFamily: theme.fontSemiBold,
      color: theme.text,
      marginTop: 12,
    },
    uploadCardStatus: {
      fontSize: 14,
      color: theme.textSecondary,
      marginTop: 4,
    },
    optionalDocsGrid: {
      flexDirection: 'row',
      gap: 12,
    },
    buttonGroup: {
      marginTop: 24,
    },
    primaryButton: {
      backgroundColor: theme.primary,
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'center',
      paddingVertical: 16,
      borderRadius: 12,
      gap: 8,
    },
    primaryButtonText: {
      color: '#FFFFFF',
      fontSize: 16,
      fontFamily: theme.fontSemiBold,
    },
    secondaryButton: {
      backgroundColor: theme.surface,
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'center',
      paddingVertical: 16,
      borderRadius: 12,
      gap: 8,
      borderWidth: 2,
      borderColor: theme.primary,
      marginBottom: 12,
    },
    secondaryButtonText: {
      color: theme.primary,
      fontSize: 16,
      fontFamily: theme.fontSemiBold,
    },
    buttonDisabled: {
      opacity: 0.5,
      borderColor: theme.textSecondary,
    },
    linkButton: {
      alignItems: 'center',
      paddingVertical: 12,
    },
    linkButtonText: {
      color: theme.primary,
      fontSize: 14,
      fontFamily: theme.fontMedium,
    },
    infoCard: {
      flexDirection: 'row',
      alignItems: 'center',
      backgroundColor: isDark ? '#1E3A8A' : '#E3F2FD',
      padding: 16,
      borderRadius: 12,
      marginBottom: 24,
      gap: 12,
    },
    infoText: {
      flex: 1,
      fontSize: 14,
      color: isDark ? '#BFDBFE' : '#1565C0',
      lineHeight: 20,
    },
  });

  return (
    <View style={styles.container}>
      <StatusBar style={isDark ? 'light' : 'dark'} />

      <Header title="Profile Setup" showBack={false} showNotifications={false} showSearch={false} />

      <View style={{ paddingTop: 8 }}>
        <View style={styles.stepIndicatorContainer}>
          <View style={[styles.stepDot, currentStep !== 'welcome' && styles.stepDotActive]} />
          <View style={[styles.stepDot, currentStep === 'skills' && styles.stepDotActive]} />
          <View style={[styles.stepDot, currentStep === 'complete' && styles.stepDotActive]} />
        </View>
      </View>

      <ScrollView
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {currentStep === 'welcome' && renderWelcomeStep()}
        {currentStep === 'documents' && renderDocumentsStep()}
        {currentStep === 'skills' && renderSkillsStep()}
      </ScrollView>
    </View>
  );
}
