import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Modal,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  Image,
  ScrollView,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as ImagePicker from 'expo-image-picker';
import { useTranslation } from 'react-i18next';

interface PaymentScreenshotModalProps {
  visible: boolean;
  paymentData: any;
  onClose: () => void;
  onSubmit: (screenshot: any) => void;
  onSkip: () => void;
}

export default function PaymentScreenshotModal({
  visible,
  paymentData,
  onClose,
  onSubmit,
  onSkip,
}: PaymentScreenshotModalProps) {
  const [screenshot, setScreenshot] = useState<any>(null);
  const [uploading, setUploading] = useState(false);
  const { t } = useTranslation();

  // Clear screenshot and reset state when modal opens or closes
  useEffect(() => {
    console.log('PaymentScreenshotModal - visible:', visible, 'paymentData:', paymentData);
    
    if (!visible) {
      // Clear all state when modal closes
      setScreenshot(null);
      setUploading(false);
    }
  }, [visible]);

  const requestPermissions = async () => {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert(
        t('paymentScreenshot.permissionRequired'),
        t('paymentScreenshot.galleryPermission')
      );
      return false;
    }
    return true;
  };

  const pickImage = async () => {
    const hasPermission = await requestPermissions();
    if (!hasPermission) return;

    try {
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: true,
        aspect: [3, 4],
        quality: 0.8,
      });

      if (!result.canceled && result.assets[0]) {
        setScreenshot(result.assets[0]);
      }
    } catch (error) {
      console.error('Error picking image:', error);
      Alert.alert(t('common.error'), t('paymentScreenshot.failedPickImage'));
    }
  };

  const takePhoto = async () => {
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert(
        t('paymentScreenshot.permissionRequired'),
        t('paymentScreenshot.cameraPermission')
      );
      return;
    }

    try {
      const result = await ImagePicker.launchCameraAsync({
        allowsEditing: true,
        aspect: [3, 4],
        quality: 0.8,
      });

      if (!result.canceled && result.assets[0]) {
        setScreenshot(result.assets[0]);
      }
    } catch (error) {
      console.error('Error taking photo:', error);
      Alert.alert(t('common.error'), t('paymentScreenshot.failedTakePhoto'));
    }
  };

  const handleSubmit = () => {
    if (!screenshot) {
      Alert.alert(
        t('paymentScreenshot.noScreenshot'),
        t('paymentScreenshot.noScreenshotMsg'),
        [
          { text: t('paymentScreenshot.uploadScreenshot'), style: 'default' },
          { text: t('paymentScreenshot.skip'), onPress: onSkip, style: 'cancel' },
        ]
      );
      return;
    }
    
    setUploading(true);
    onSubmit(screenshot);
  };

  const handleSkip = () => {
    Alert.alert(
      t('paymentScreenshot.skipTitle'),
      t('paymentScreenshot.skipMsg'),
      [
        { text: t('common.cancel'), style: 'cancel' },
        { text: t('paymentScreenshot.skip'), onPress: onSkip, style: 'destructive' },
      ]
    );
  };

  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent={true}
      onRequestClose={() => {}} // Prevent back button from closing
    >
      <View style={styles.overlay}>
        <View style={styles.modal}>
          {/* Header - No close button */}
          <View style={styles.header}>
            <Text style={styles.headerTitle}>{t('paymentScreenshot.title')}</Text>
            <View style={{ width: 24 }} />
          </View>

          <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
            {/* Payment Info */}
            <View style={styles.paymentInfo}>
              <Ionicons name="checkmark-circle" size={48} color="#10b981" />
              <Text style={styles.successText}>{t('paymentScreenshot.paymentInitiated')}</Text>
              <Text style={styles.infoText}>
                {t('paymentScreenshot.transactionId')} {paymentData?.transaction_id}
              </Text>
            </View>

            {/* Instructions */}
            <View style={styles.instructionsBox}>
              <Ionicons name="information-circle" size={24} color="#14b8a6" />
              <View style={styles.instructionsTextContainer}>
                <Text style={styles.instructionsText}>
                  {t('paymentScreenshot.uploadInstructions')}
                </Text>
                <Text style={styles.deadlineText}>
                  {t('paymentScreenshot.uploadDeadline')}
                </Text>
              </View>
            </View>

            {/* Screenshot Preview */}
            {screenshot && (
              <View style={styles.previewContainer}>
                <Text style={styles.label}>{t('paymentScreenshot.screenshotPreview')}</Text>
                <Image source={{ uri: screenshot.uri }} style={styles.preview} />
                <TouchableOpacity
                  style={styles.removeButton}
                  onPress={() => setScreenshot(null)}
                  disabled={uploading}
                >
                  <Ionicons name="trash" size={20} color="#ef4444" />
                  <Text style={styles.removeText}>{t('paymentScreenshot.remove')}</Text>
                </TouchableOpacity>
              </View>
            )}

            {/* Upload Buttons */}
            {!screenshot && (
              <View style={styles.uploadButtons}>
                <TouchableOpacity
                  style={styles.uploadButton}
                  onPress={pickImage}
                  disabled={uploading}
                >
                  <Ionicons name="images" size={32} color="#14b8a6" />
                  <Text style={styles.uploadButtonText}>{t('paymentScreenshot.chooseGallery')}</Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={styles.uploadButton}
                  onPress={takePhoto}
                  disabled={uploading}
                >
                  <Ionicons name="camera" size={32} color="#14b8a6" />
                  <Text style={styles.uploadButtonText}>{t('paymentScreenshot.takePhoto')}</Text>
                </TouchableOpacity>
              </View>
            )}

            {/* Action Buttons */}
            <View style={styles.actionButtons}>
              <TouchableOpacity
                style={[styles.submitButton, uploading && styles.buttonDisabled]}
                onPress={handleSubmit}
                disabled={uploading}
              >
                {uploading ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <>
                    <Ionicons name="checkmark" size={20} color="#fff" />
                    <Text style={styles.submitButtonText}>
                      {screenshot ? t('paymentScreenshot.submitWithScreenshot') : t('paymentScreenshot.submitAnyway')}
                    </Text>
                  </>
                )}
              </TouchableOpacity>

              <TouchableOpacity
                style={styles.skipButton}
                onPress={handleSkip}
                disabled={uploading}
              >
                <Text style={styles.skipButtonText}>{t('paymentScreenshot.skipForNow')}</Text>
              </TouchableOpacity>
            </View>
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
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
    paddingBottom: 20,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#e5e7eb',
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#1f2937',
  },
  content: {
    padding: 20,
  },
  paymentInfo: {
    alignItems: 'center',
    marginBottom: 24,
    padding: 20,
    backgroundColor: '#f0fdf4',
    borderRadius: 12,
  },
  successText: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#10b981',
    marginTop: 12,
  },
  infoText: {
    fontSize: 14,
    color: '#6b7280',
    marginTop: 8,
  },
  instructionsBox: {
    flexDirection: 'row',
    backgroundColor: '#f0fdfa',
    padding: 16,
    borderRadius: 12,
    marginBottom: 24,
  },
  instructionsTextContainer: {
    flex: 1,
    marginLeft: 12,
  },
  instructionsText: {
    fontSize: 14,
    color: '#115e59',
    lineHeight: 20,
    marginBottom: 8,
  },
  deadlineText: {
    fontSize: 13,
    color: '#dc2626',
    fontWeight: '600',
    lineHeight: 18,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#374151',
    marginBottom: 8,
  },
  previewContainer: {
    marginBottom: 24,
  },
  preview: {
    width: '100%',
    height: 300,
    borderRadius: 12,
    backgroundColor: '#f3f4f6',
  },
  removeButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 12,
    padding: 12,
    borderRadius: 8,
    backgroundColor: '#fee2e2',
  },
  removeText: {
    marginLeft: 8,
    fontSize: 14,
    fontWeight: '600',
    color: '#ef4444',
  },
  uploadButtons: {
    gap: 12,
    marginBottom: 24,
  },
  uploadButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 20,
    borderRadius: 12,
    backgroundColor: '#fff',
    borderWidth: 2,
    borderColor: '#14b8a6',
    borderStyle: 'dashed',
  },
  uploadButtonText: {
    marginLeft: 12,
    fontSize: 16,
    fontWeight: '600',
    color: '#14b8a6',
  },
  actionButtons: {
    gap: 12,
  },
  submitButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#14b8a6',
    padding: 16,
    borderRadius: 12,
    gap: 8,
  },
  submitButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  buttonDisabled: {
    backgroundColor: '#9ca3af',
  },
  skipButton: {
    alignItems: 'center',
    padding: 16,
  },
  skipButtonText: {
    color: '#6b7280',
    fontSize: 14,
    fontWeight: '600',
  },
});
