/*  file: msg.h
 *  Author: Auto-generated by mkqueue.py
 */

#ifndef __MSG_H
#define __MSG_H

#ifdef __cplusplus
extern "C" {
#endif

// ================================= Includes ==================================
#include <stdio.h>

// ============================== Exported Macros ==============================
#define MSG_QUEUE_ITEMS                               (8)
#define MSG_QUEUE_OK                               (0x00)
#define MSG_QUEUE_FULL                             (0x01)
#define MSG_QUEUE_EMPTY                            (0x02)

// ============================= Exported Typedefs =============================
// Modify this definition to fit your application
typedef uint8_t msg_t;

// ======================= Exported Function Prototypes ========================
void MSGQUEUE_Init(void);
uint8_t MSGQUEUE_Add(msg_t *item);
uint8_t MSGQUEUE_Get(volatile msg_t *item);
uint8_t MSGQUEUE_Status(void);

#ifdef __cplusplus
}
#endif

#endif // __MSG_H

