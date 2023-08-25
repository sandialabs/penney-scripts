/*  File: test.c
 *  Author: Auto-generated by mkqueue.py
 */

#include "test.h"

// ============================= Private Typedefs ==============================
typedef struct {
  uint8_t pIn;
  uint8_t pOut;
  uint8_t full;
  puppy_t queue[PUPPY_QUEUE_ITEMS];
} puppy_queue_t;

// ============================= Private Variables =============================
static puppy_queue_t puppy_queue;

// =========================== Function Definitions ============================
void PUPPYQUEUE_Init(void) {
  puppy_queue.pIn = 0;
  puppy_queue.pOut = 0;
  puppy_queue.full = 0;
  return;
}

uint8_t PUPPYQUEUE_Add(puppy_t *item) {
  // If full, return error
  if (puppy_queue.full) {
    return PUPPY_QUEUE_FULL;
  }
  // Copy item into queue
  for (int n = 0; n < sizeof(puppy_t); n++) {
    *((uint8_t *)&(puppy_queue.queue[puppy_queue.pIn]) + n) = *((uint8_t *)item + n);
  }
  // Wrap pIn at boundary
  if (puppy_queue.pIn == PUPPY_QUEUE_ITEMS - 1) {
    puppy_queue.pIn = 0;
  } else {
    puppy_queue.pIn++;
  }
  // Check for full condition
  if (puppy_queue.pIn == puppy_queue.pOut) {
    puppy_queue.full = 1;
  }
  return PUPPY_QUEUE_OK;
}

uint8_t PUPPYQUEUE_Get(volatile puppy_t *item) {
  // Check for empty queue
  if ((puppy_queue.pIn == puppy_queue.pOut) && (puppy_queue.full == 0)) {
    return PUPPY_QUEUE_EMPTY;
  }
  // Copy next data from the queue to item
  for (int n = 0; n < sizeof(puppy_t); n++) {
    *((uint8_t *)item + n) = *((uint8_t *)&(puppy_queue.queue[puppy_queue.pOut]) + n);
  }
  // Wrap pOut at boundary
  if (puppy_queue.pOut == PUPPY_QUEUE_ITEMS - 1) {
    puppy_queue.pOut = 0;
  } else {
    puppy_queue.pOut++;
  }
  // Clear full condition
  puppy_queue.full = 0;
  return PUPPY_QUEUE_OK;
}

uint8_t PUPPYQUEUE_Status(void) {
  if ((puppy_queue.pIn == puppy_queue.pOut) && (puppy_queue.full == 0)) {
    return PUPPY_QUEUE_EMPTY;
  }
  if (puppy_queue.full) {
    return PUPPY_QUEUE_FULL;
  }
  // If not full or empty, it is non-empty (at least one item in queue)
  return PUPPY_QUEUE_OK;
}

